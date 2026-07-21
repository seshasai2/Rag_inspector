# UI Test Checklist (Phase 7)

Sign in as demo user before app pages. Mark Pass/Fail.

| Page | Loads | Nav | Forms | Buttons | Tables | Charts | Filters | Search | Pagination | Errors | Responsive | Empty | Loading | Failure |
|------|-------|-----|-------|---------|--------|--------|---------|--------|------------|--------|------------|-------|---------|---------|
| `/` landing | | | | | — | — | — | — | — | | | — | | |
| `/auth/login` | | | | | — | — | — | — | — | invalid creds | | — | | |
| `/auth/register` | | | | | — | — | — | — | — | dup email | | — | | |
| `/auth/forgot-password` | | | | | — | — | — | — | — | | | — | | |
| `/dashboard` | | | | | | | pipeline | — | — | | | no traces | | |
| `/queries` | | | | | | — | failure type | | | | | empty list | | |
| `/queries/[id]` | | | | grounding | chunks | gauge | — | — | — | 404 id | | | | |
| `/chunks` | | | | flag | | | | | | | | | | |
| `/knowledge/gaps` | | | | status | | — | | | | | | | | |
| `/autofix` | | | | apply/dismiss | | — | | | | | | | | |
| `/documents` | | | create | | | — | freshness | | | | | | | |
| `/monitoring` | | | config | run-now | history | | | | | | | | | |
| `/regression` | | | | compare | snaps | | | | | | | | | |
| `/benchmark` | | | | run | | | | | | | | | | |
| `/studio` | | | prompt | analyze | — | — | — | — | — | | | | | |
| `/investigator` | | | ask | | — | — | — | — | — | | | | | |
| `/executive` | | | | export | history | | | | | | | | | |
| `/team` | | | invite | | members | — | — | — | — | | | | | |
| `/metrics` | | | | | | timeseries | days | — | — | | | | | |
| `/pipelines` | | | create/edit | | | — | — | — | — | | | | | |
| `/settings` | | | prefs/keys | create key | keys | — | — | — | — | | | | | |
| `/admin` | | | | user status | users/jobs | — | — | — | — | 403 non-admin | | | | |
| `/enterprise` | | | | | — | — | — | — | — | honesty banner | | | | |
| `/privacy` `/terms` `/refund-policy` | | | — | — | — | — | — | — | — | | | — | — | |

## Empty / loading / failure checks

1. **Empty:** new registered user before seed — dashboard zeros, empty queries (not crash).
2. **Loading:** throttle network; confirm skeletons/spinners dismiss.
3. **Failure:** stop API (`docker stop …_backend`) → UI shows error / login redirect, not white screen.

## Navigation

Sidebar/top nav reaches every app route above without 404. Middleware redirects unauthenticated users to `/auth/login`.
