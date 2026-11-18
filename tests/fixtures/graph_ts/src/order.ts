import { charge } from "./payment";

export function cancel(orderId: string): string {
  charge(1);
  return `cancelled:${orderId}`;
}
