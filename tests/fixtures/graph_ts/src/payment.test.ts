import { charge } from "./payment";

test("charge", () => {
  expect(charge(1)).toBe(1);
});
