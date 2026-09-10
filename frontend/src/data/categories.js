export const INCOME_CATEGORIES = [
  "Salary",
  "Freelance",
  "Business",
  "Investment",
  "Other",
];

export const EXPENSE_CATEGORIES = [
  "Food",
  "Rent",
  "Transport",
  "Shopping",
  "Entertainment",
  "Bills",
  "Health",
  "Education",
  "Other",
];

// A stable color per category so charts stay visually consistent
// across the Dashboard and Reports pages.
export const CATEGORY_COLORS = {
  Salary: "#0F6E5C",
  Freelance: "#2E9D6F",
  Business: "#4CB98A",
  Investment: "#7FC7A9",
  Food: "#C24A3B",
  Rent: "#B0562E",
  Transport: "#C77A2E",
  Shopping: "#B8862E",
  Entertainment: "#8A6FB0",
  Bills: "#4A7FB0",
  Health: "#3B9AA8",
  Education: "#5D7A9E",
  Other: "#8C8C8C",
};

export function categoriesForType(type) {
  return type === "income" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;
}
