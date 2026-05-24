export type OrderSide = "BUY" | "SELL";
export type OrderType = "MARKET" | "LIMIT";
export type OrderStatus = "EXECUTED" | "REJECTED";

export interface PlaceOrderRequest {
  ticker: string;
  side: OrderSide;
  quantity: number;
  order_type: OrderType;
  limit_price?: number;
}

export interface Order {
  id: string;
  user_id: string;
  ticker: string;
  side: OrderSide;
  quantity: number;
  order_type: OrderType;
  limit_price: number | null;
  executed_price: number | null;
  status: OrderStatus;
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
