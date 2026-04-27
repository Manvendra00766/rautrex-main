import jsPDF from "jspdf"
import autoTable from "jspdf-autotable"

export function exportBacktestPDF(data: any, ticker: string, strategy: string) {
  const doc = new jsPDF()
  const date = new Date().toLocaleDateString()
  
  // Header
  doc.setFontSize(20)
  doc.setTextColor(0, 212, 255)
  doc.text("RAUTREX", 14, 20)
  
  doc.setFontSize(14)
  doc.setTextColor(0, 0, 0)
  doc.text(`Backtest Report — ${ticker} — ${strategy}`, 14, 32)
  doc.setFontSize(10)
  doc.setTextColor(100, 100, 100)
  doc.text(`Generated: ${date}`, 14, 40)

  // Metrics section
  doc.setFontSize(12)
  doc.setTextColor(0, 0, 0)
  doc.text("Performance Metrics", 14, 55)
  
  const metrics = data.metrics?.strategy || data
  
  autoTable(doc, {
    startY: 60,
    head: [["Metric", "Value"]],
    body: [
      ["Total Return", (metrics.total_return * 100).toFixed(2) + "%"],
      ["CAGR", (metrics.cagr * 100).toFixed(2) + "%"],
      ["Sharpe Ratio", metrics.sharpe_ratio?.toFixed(2) || metrics.sharpe?.toFixed(2)],
      ["Max Drawdown", (metrics.max_drawdown * 100).toFixed(2) + "%"],
      ["Win Rate", (metrics.win_rate * 100).toFixed(2) + "%"],
      ["Total Trades", metrics.total_trades],
    ],
    theme: "grid",
    headStyles: { fillColor: [0, 212, 255] as any, textColor: [0, 0, 0] },
  })

  // Trade log table if available
  const trades = data.trades || data.trade_log
  if (trades && trades.length > 0) {
    doc.text("Trade Log", 14, (doc as any).lastAutoTable.finalY + 15)
    autoTable(doc, {
      startY: (doc as any).lastAutoTable.finalY + 20,
      head: [["Entry Date", "Exit Date", "Entry Price", "Exit Price", "PnL", "Return %"]],
      body: trades.map((t: any) => [
        t.entry_date,
        t.exit_date,
        t.entry_price?.toFixed(2),
        t.exit_price?.toFixed(2),
        t.net_pnl?.toFixed(2) || t.pnl_value?.toFixed(2),
        (t.return_pct * 100).toFixed(2) + "%"
      ]),
      theme: "striped",
      headStyles: { fillColor: [40, 40, 60] as any },
    })
  }

  // TRIGGER DOWNLOAD
  const filename = `Backtest_${ticker}_${strategy}_${date.replace(/\//g, '-')}.pdf`
  doc.save(filename)
}

export function exportMonteCarloPDF(data: any, ticker: string) {
  const doc = new jsPDF()
  const date = new Date().toLocaleDateString()
  
  doc.setFontSize(20)
  doc.setTextColor(0, 212, 255)
  doc.text("RAUTREX", 14, 20)
  
  doc.setFontSize(14)
  doc.setTextColor(0, 0, 0)
  doc.text(`Monte Carlo Simulation — ${ticker}`, 14, 32)
  doc.setFontSize(10)
  doc.setTextColor(100, 100, 100)
  doc.text(`Generated: ${date}`, 14, 40)

  autoTable(doc, {
    startY: 50,
    head: [["Metric", "Value"]],
    body: [
      ["Expected Value", "$" + data.expected_value?.toLocaleString()],
      ["Value at Risk (95%)", "$" + data.var?.toLocaleString()],
      ["Prob. of Profit", data.prob_profit?.toFixed(2) + "%"],
      ["Forecast Volatility", (data.volatility * 100).toFixed(2) + "%"],
      ["Best Case", "$" + data.best_case?.toLocaleString()],
      ["Worst Case", "$" + data.worst_case?.toLocaleString()],
    ],
    theme: "grid",
    headStyles: { fillColor: [0, 212, 255] as any, textColor: [0, 0, 0] },
  })

  doc.save(`MonteCarlo_${ticker}_${date.replace(/\//g, '-')}.pdf`)
}

export function exportRiskPDF(data: any, portfolio: string) {
  const doc = new jsPDF()
  const date = new Date().toLocaleDateString()
  
  doc.setFontSize(20)
  doc.setTextColor(0, 212, 255)
  doc.text("RAUTREX", 14, 20)
  
  doc.setFontSize(14)
  doc.setTextColor(0, 0, 0)
  doc.text(`Risk Audit Report — ${portfolio}`, 14, 32)
  
  const metrics = data.metrics || {}

  autoTable(doc, {
    startY: 50,
    head: [["Risk Metric", "Value"]],
    body: [
      ["Risk Score", data.risk_score?.toFixed(1)],
      ["Annualized Volatility", (metrics.volatility * 100).toFixed(2) + "%"],
      ["Sharpe Ratio", metrics.sharpe?.toFixed(2)],
      ["Max Drawdown", (metrics.max_drawdown * 100).toFixed(2) + "%"],
      ["Value at Risk (95%)", (metrics.var_95 * 100).toFixed(2) + "%"],
      ["Portfolio Beta", metrics.beta?.toFixed(2)],
      ["Portfolio Alpha", (metrics.alpha * 100).toFixed(2) + "%"],
    ],
    theme: "grid",
    headStyles: { fillColor: [255, 77, 77] as any, textColor: [255, 255, 255] },
  })

  doc.save(`Risk_Audit_${date.replace(/\//g, '-')}.pdf`)
}

export function exportOptionsPDF(data: any, ticker: string) {
  const doc = new jsPDF()
  const date = new Date().toLocaleDateString()
  
  doc.setFontSize(20)
  doc.setTextColor(0, 212, 255)
  doc.text("RAUTREX", 14, 20)
  
  doc.setFontSize(14)
  doc.setTextColor(0, 0, 0)
  doc.text(`Options Analysis — ${ticker}`, 14, 32)

  if (data.price) {
    autoTable(doc, {
      startY: 50,
      head: [["Option Greek", "Value"]],
      body: [
        ["Model Price", "$" + data.price.toFixed(2)],
        ["Delta", data.greeks?.delta?.toFixed(4)],
        ["Gamma", data.greeks?.gamma?.toFixed(4)],
        ["Theta", data.greeks?.theta?.toFixed(4)],
        ["Vega", data.greeks?.vega?.toFixed(4)],
        ["Rho", data.greeks?.rho?.toFixed(4)],
      ],
      theme: "grid",
    })
  }

  doc.save(`Options_Analysis_${ticker}_${date.replace(/\//g, '-')}.pdf`)
}
