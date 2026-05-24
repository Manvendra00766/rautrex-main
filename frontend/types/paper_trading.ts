export interface PlaceOrderRequest {
  ticker: string;
  side: "BUY" | "SELL";
  quantity: number;
  order_type: "MARKET" | "LIMIT";
  limit_price?: number;
}

export interface Order {
  id: string;
  user_id: string;
  ticker: string;
  side: string;
  quantity: number;
  order_type: string;
  limit_price?: number;
  executed_price?: number;
  status: "EXECUTED" | "REJECTED";
  created_at: string;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_buy_price: number;
  current_price: number;
  pnl: number;
  pnl_pct: number;
  total_value: number;
}

export interface Portfolio {
  cash_balance: number;
  total_invested: number;
  total_current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  positions: Position[];
}
