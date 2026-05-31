from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.logger import logger
from models.user_data import UserPortfolio, PortfolioPosition, PortfolioMetricsCache

class ChatbotContextService:
    async def build_rag_context(self, user_id: str, db: AsyncSession) -> str:
        """
        Intercepts chatbot messages and queries the local cache and holdings to build a
        highly structured, verified XML context block, preventing the LLM from hallucinating numbers.
        """
        try:
            # 1. Fetch user's default/first portfolio
            portfolio_stmt = select(UserPortfolio).where(UserPortfolio.user_id == user_id).limit(1)
            portfolio_res = await db.execute(portfolio_stmt)
            portfolio = portfolio_res.scalar_one_or_none()
            
            if not portfolio:
                return "<portfolio_verification_data>\n  <error>No portfolio found for this user.</error>\n</portfolio_verification_data>"

            portfolio_id = portfolio.id

            # 2. Fetch active holdings/positions
            pos_stmt = select(PortfolioPosition).where(PortfolioPosition.portfolio_id == portfolio_id)
            pos_res = await db.execute(pos_stmt)
            positions = pos_res.scalars().all()

            positions_xml = ""
            for pos in positions:
                positions_xml += f"    <position ticker=\"{pos.ticker}\" shares=\"{pos.shares}\" avg_cost=\"{pos.avg_cost_price:.2f}\" />\n"

            # 3. Fetch pre-calculated risk metrics from local SQLite cache
            metrics_stmt = select(PortfolioMetricsCache).where(PortfolioMetricsCache.portfolio_id == str(portfolio_id))
            metrics_res = await db.execute(metrics_stmt)
            metrics = metrics_res.scalar_one_or_none()

            metrics_xml = ""
            if metrics:
                metrics_xml = (
                    f"    <sharpe_ratio>{metrics.sharpe_ratio}</sharpe_ratio>\n"
                    f"    <max_drawdown>{metrics.max_drawdown}%</max_drawdown>\n"
                    f"    <value_at_risk_95>{metrics.value_at_risk}%</value_at_risk_95>\n"
                    f"    <beta>{metrics.beta}</beta>\n"
                    f"    <last_calculated>{metrics.updated_at.isoformat() if metrics.updated_at else 'Unknown'}</last_calculated>\n"
                )
            else:
                metrics_xml = "    <metrics_status>Not yet calculated</metrics_status>\n"

            # 4. Assemble the final structured XML block
            xml_block = (
                "<portfolio_verification_data>\n"
                f"  <portfolio name=\"{portfolio.name}\" id=\"{portfolio.id}\">\n"
                "  <positions>\n"
                f"{positions_xml}"
                "  </positions>\n"
                "  <metrics>\n"
                f"{metrics_xml}"
                "  </metrics>\n"
                "  </portfolio>\n"
                "</portfolio_verification_data>"
            )
            return xml_block

        except Exception as e:
            logger.error(f"[ChatbotContext] Failed building RAG XML block for user {user_id}: {e}")
            return "<portfolio_verification_data>\n  <error>Failed to load portfolio metrics.</error>\n</portfolio_verification_data>"

chatbot_context_service = ChatbotContextService()
