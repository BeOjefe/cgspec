# 02-OOUX: Object-Oriented UX & Domain Mental Model

- **Status:** `[Drafting]`
- **Framework:** `Sophia Prater ORCA (Objects, Relationships, Calls-to-action, Attributes)`
- **Stage:** `1. Domain Modeling`

---

## 1. Domain Nouns & Core Mental Model
*Identify the 3–7 primary domain nouns the user thinks about:*

### Noun 1: `[PrimaryNounA]`
- **Definition:** [What is this object in the user's mental model?]
- **Attributes:** `id`, `name`, `status`, `created_at`, `updated_at`.
- **Relationships:** Belongs to `[PrimaryNounB]`. Has many `[ChildNoun]`.
- **Core User Actions (Calls-to-Action):** `Create`, `Edit`, `Archive`, `Delete`.

---

## 2. Object Lifecycle Matrix & Permissions
Map each domain noun across the 6 granular permissions:

| Domain Noun | `read` | `invoke` | `propose_edit` | `write` | `share` | `admin` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`[PrimaryNounA]`** | Anyone | Authenticated | Member | Owner | Owner | Admin |

---

## 3. Mapping Domain Nouns to Focal Screens
- **`SCR-01` [Screen Name]:** Manages `[PrimaryNounA]` and related list workflows.
- **`SCR-02` [Screen Name]:** Manages `[PrimaryNounB]` and inspection details.
