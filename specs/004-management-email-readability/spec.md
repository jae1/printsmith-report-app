# Feature Specification: Management Email Readability

**Status**: In progress
**Input**: Restore the earlier clear email layout after the expanded summary and
stacked cards proved harder to scan and poorly aligned.

## User Scenario

Management opens the daily email on a phone or desktop and first sees the large
collected-today total, the new-order count and value, then compact two-column
cards in the familiar section order. Amounts line up on the right.

## Requirements

- The HTML restores the earlier single collected-today highlight, new-order
  count and value card, and five familiar detail sections. The expanded summary
  grid and individual new-order cards are removed.
- Each detail card keeps its title on the left and amount on the right, with
  consistent widths and spacing at phone and desktop sizes.
- Paid Today cards use the report's `is_partial` and `current_balance` fields;
  payment type and method remain visible.
- Order values use a neutral color; collected amounts and spending remain
  visually distinct without relying on color alone.
- HTML remains readable in common email clients, and the plain-text alternative
  contains the same summary and five detail sections.
- The configured report title prefix is used in the email title and subject.
- Report classification, payment amounts, SMTP credentials, recipients, and
  scheduler behavior remain unchanged.

## Data and Verification

Use `get_report_data` section rows, `spending_service.get_spending_by_date`, and
`settings_service.load_settings`. Render a sample with a partial payment,
spending item, and all operational sections at phone and desktop widths; inspect
both MIME alternatives and the subject without sending an email.
