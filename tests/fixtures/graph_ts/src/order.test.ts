import { cancel } from "./order";

test("cancel", () => {
  expect(cancel("o-1")).toContain("cancelled");
});
