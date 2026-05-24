import re
from typing import Dict, Any, List

class AIMarketIntelligence:
    def __init__(self):
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            self.analyzer = SentimentIntensityAnalyzer()
        except ImportError:
            self.analyzer = None

    def analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyzes sentiment of news headlines or market commentary."""
        if not self.analyzer:
            return {"sentiment": "NEUTRAL", "score": 0.0}
            
        scores = self.analyzer.polarity_scores(text)
        compound = scores['compound']
        
        if compound >= 0.05:
            sentiment = "BULLISH"
        elif compound <= -0.05:
            sentiment = "BEARISH"
        else:
            sentiment = "NEUTRAL"
            
        return {
            "sentiment": sentiment,
            "score": compound,
            "details": scores
        }

    def generate_market_commentary(self, portfolio_returns: float, market_returns: float) -> str:
        """Generates AI market commentary based on portfolio performance vs benchmark."""
        if portfolio_returns > market_returns + 0.02:
            return "The portfolio has significantly outperformed the broader market, driven by strong alpha generation in key holdings."
        elif portfolio_returns > market_returns:
            return "The portfolio is slightly ahead of the market benchmark, showing steady relative strength."
        elif portfolio_returns > market_returns - 0.02:
            return "The portfolio is tracking closely with the broader market, indicating a high correlation with macro trends."
        else:
            return "The portfolio has underperformed the market recently. A review of sector exposures and recent drawdowns is recommended."

    def why_market_moved(self, price_change_pct: float, volume_spike: bool, news_headlines: List[str] = None) -> str:
        """Heuristic engine to explain asset price movement."""
        reasons = []
        
        if abs(price_change_pct) > 0.05:
            direction = "surged" if price_change_pct > 0 else "plummeted"
            reasons.append(f"The asset {direction} by {price_change_pct*100:.1f}%.")
            
            if volume_spike:
                reasons.append("This move was supported by abnormally high trading volume, indicating strong institutional conviction.")
                
            if news_headlines and self.analyzer:
                # Average sentiment of headlines
                sentiments = [self.analyzer.polarity_scores(h)['compound'] for h in news_headlines]
                avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
                
                if avg_sentiment > 0.2 and price_change_pct > 0:
                    reasons.append("Positive news catalysts likely drove the upward momentum.")
                elif avg_sentiment < -0.2 and price_change_pct < 0:
                    reasons.append("Negative headlines and bearish sentiment heavily influenced the sell-off.")
                else:
                    reasons.append("The price action appears to be driven by technical factors or unlisted catalysts, diverging from headline sentiment.")
                    
        else:
            reasons.append(f"The asset traded flat, moving only {price_change_pct*100:.1f}%. Market conditions remain range-bound.")
            
        return " ".join(reasons)
