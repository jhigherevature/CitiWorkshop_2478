# Citi Workshop Refresher

This is three weeks of hands-on refresher work leading up to the Citi workshop. The workshop is a three-day, hackathon-style event where you'll build a full-stack application from scratch: FastAPI and PostgreSQL with SQLAlchemy, a React and Material UI frontend, JWT login with role-based access, and deployment to AWS.

You've built one of these before. The point of these three weeks is to keep that knowledge fresh and to get faster at it, so that on workshop day the setup and plumbing come automatically and your time goes into the problem in front of you.

## How the days work

- **Hours:** half days, **10:00 AM – 2:00 PM ET**.
- **Zoom:** a short check-in opens the day and another closes it. The time in between is for working.
- **Discord:** questions, blockers, and requests for a second pair of eyes go here, at any point in the day. Answers come asynchronously, so include what you ran and the full error message; that's usually enough to get an answer on the first reply.
- **Fridays:** everyone presents their work.

## The three weeks

| Week | Focus |
|---|---|
| **1** | **A new project.** Pick a problem statement in [`Projects/`](Projects/) that you *didn't* build during training, and build it start to finish. |
| **2** | **Deployment and stretch goals.** Get the project running on AWS, then take on stretch goals. |
| **3** | **Review, polish, and prepare.** Finish anything outstanding, tidy up what's there, and get ready for the workshop. |

### Week 2: deployment

[`AWS-Deployment.md`](Projects/stretch-goals/AWS-Deployment.md) is the main goal for the week. It follows the same deployment shape as the original training: Lambda, RDS, S3, and CloudFront. You'll be using your own AWS account, so read its first section and set up the budget in Step 1 **before creating anything else**. When you finish for the day, stop the RDS instance.

Once the project is live, pick from the stretch goals. Each is sized:

| Stretch goal | Size |
|---|---|
| [Dark mode toggle](Projects/stretch-goals/stretch-dark-mode.md) | S (1 point) |
| [Health check endpoints](Projects/stretch-goals/stretch-health-checks.md) | S (1 point) |
| [Idempotent setup & seed scripts](Projects/stretch-goals/stretch-idempotent-scripts.md) | M (2 points) |
| [Refresh tokens](Projects/stretch-goals/stretch-refresh-tokens.md) | M (2 points) |
| [Server-side pagination, filtering & sorting](Projects/stretch-goals/stretch-pagination-filtering-sorting.md) | L (3 points) |
| [Permission-based roles](Projects/stretch-goals/stretch-permission-based-roles.md) | L (3 points) |
| [Soft deletes with audit trail](Projects/stretch-goals/stretch-soft-deletes-audit-trail.md) | L (3 points) |

## What's in this folder

### [`Projects/`](Projects/)

The three problem statements, [AgriCore](Projects/problem_statement_agricore.md), [CashCow](Projects/problem_statement_cashcow.md), and [MedFlow](Projects/problem_statement_medflow.md), plus [`stretch-goals/`](Projects/stretch-goals/), which holds the deployment guide and the stretch goals listed above.

### [`Labs/`](Labs/)

Four short, guided labs. Each one is the smallest thing that actually runs for one layer of the stack, with nearly all the code provided and explained. They use a simple library domain, deliberately unlike the projects, so the plumbing stays easy to see. Use them to warm up, or come back to one when that layer of your project stops making sense.

| Lab | What it shows |
|---|---|
| [One Endpoint, One Table](Labs/one-endpoint-one-table/) | The full path of a request through FastAPI: route, dependency, session, query, schema, response |
| [Login and a Locked Door](Labs/login-and-a-locked-door/) | bcrypt, JWTs, `get_current_user`, role checks, and `401` versus `403` |
| [Five Rows on a Page](Labs/five-rows-on-a-page/) | A React frontend logging in and rendering protected data: axios interceptor, auth context, DataGrid |
| [Counting Things](Labs/counting-things/) | The query shapes behind the Co-Location Discrepancy, Maintenance Flags, and Reporting Lines questions, in SQL and SQLAlchemy side by side |

Every lab's README lists its prerequisites and setup steps, and each lab runs on its own.
