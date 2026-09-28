# Primary Goal: AWS Cloud Deployment

This is the primary focus for week 2. It follows the same shape as the deployment used in the original training, so anyone who worked through that will recognise most of it.

Every step below is written for the **AWS Console**. Where a CLI equivalent is genuinely useful — mostly the repeated steps — it's noted alongside. Nothing here requires the CLI.

---

## 1. What We're Trying to Avoid

Before the steps, it's worth being clear about *why* this deployment is shaped the way it is. Nearly every configuration choice below traces back to one concern.

**The internet finds things quickly.** Public cloud address ranges are scanned continuously and automatically. An open database port, a world-readable bucket, or an unprotected endpoint doesn't get discovered eventually — it gets discovered almost immediately, by software that never stops looking. Nothing about a small training project makes it less likely to be found. It just makes it less likely that anyone notices when it is.

**The damage usually isn't theft — it's the bill.** These projects hold invented data, so nobody is after your records. What they *are* after is free compute, free storage, and free bandwidth on someone else's account. A resource that anyone can reach is a resource anyone can drive, and on AWS the person paying is whoever owns the account.

That's why these things stay off the table:

- **Anything publicly reachable that doesn't need to be.** Every open port, public bucket, and unauthenticated endpoint is a door. Each one is worth having only if you can say what it's for.
- **Access rules that can't name a source.** "Allow from anywhere" isn't a security setting, it's the absence of one. If you can't point to a specific security group or address, the design needs changing — not the rule widening.
- **Credentials in source control.** Access keys pushed to a public repository are found by automated scanners and used, usually for mining, and the bill arrives before anyone notices. Secrets belong in environment variables and `.env` files that are gitignored, and IAM roles are better than keys wherever a role will do.
- **Permissions broader than the task.** A policy scoped to one bucket contains a mistake. A policy granting full access to a service turns the same mistake into an account-wide problem.
- **Resources that can grow without a ceiling.** Storage that expands on its own, and spending with no alert attached, both share a property: nothing stops them. Caps and alerts are what convert a surprise into a notification.
- **Anything running that nobody is watching.** This is a part-time project. Resources left up overnight, over a weekend, or after the showcase keep billing whether or not anyone is using them, and an idle resource is just as reachable as a busy one.

None of this is about being paranoid, and none of it is unusual practice — it's the ordinary shape of a deployment that someone has to walk away from. The steps that follow are simply that principle applied: default to private, name an exact source, keep secrets out of the repository, cap what can grow, and delete it when you're finished.

---

## 2. Target Architecture

```
Browser
   |
   |  HTTPS
   v
CloudFront distribution  ──(Origin Access Control)──>  S3 bucket (private)
                                                        React build output
Browser
   |
   |  HTTPS
   v
Lambda Function URL              <-- no API Gateway
   |
   v
Lambda function (FastAPI + Mangum)
   |  attached to VPC private subnets
   |
   +──(private, port 5432)──>  RDS PostgreSQL (db.t3.micro)
   |
   +──(S3 gateway endpoint)──>  S3 bucket (private)
                                 report / document uploads
```

HTTPS end to end. No EC2, no API Gateway, no NAT Gateway, no load balancer, no custom domain, and no database port open to the internet.

---

## 3. Services Used

| Service | Role |
| --- | --- |
| **Lambda** | Runs the FastAPI application |
| **Lambda Function URL** | Public HTTPS endpoint for the API |
| **RDS (PostgreSQL)** | Application database |
| **S3** (hosting bucket) | React build output, private |
| **S3** (uploads bucket) | Report and document attachments, private |
| **S3 gateway endpoint** | Lets the VPC-attached Lambda reach S3. Free |
| **CloudFront** | Serves the frontend over HTTPS |
| **IAM** | Lambda execution role |
| **CloudWatch Logs** | Lambda logs, created automatically |
| **VPC** (default) | Already exists; subnets and security groups live here |

Deliberately out of scope: API Gateway, EC2, App Runner, ECR, NAT Gateway, Route 53, Secrets Manager, ACM.

---

## 4. A Note on HTTPS

There are no certificates to deal with. CloudFront issues you a domain like `d111111abcdef8.cloudfront.net` with a certificate already attached, and the Function URL gives you `https://<id>.lambda-url.<region>.on.aws` the same way. Nothing to request, validate, or renew.

Certificates only become work if you want your own domain name, which isn't in scope here.

The one constraint HTTPS imposes: **the frontend is HTTPS, so the backend must be too.** Browsers block an HTTPS page from calling an HTTP API. That's satisfied by the plan as written, but it's why a plain HTTP backend can't be substituted later without adding TLS to it.

---

## 5. What to Create, in Order

Several steps need a value produced by an earlier one, so order matters.

### Step 1 — Budget and automatic shutdown

Do this before creating anything else. It's the safety net for every step that follows, and it costs nothing — budget monitoring is free, and so are the first two action-enabled budgets on an account.

**Billing and Cost Management → Budgets → Create budget → Customize (advanced) → Cost budget.**

| Setting | Value |
| --- | --- |
| Period | Monthly, recurring |
| Budget amount | Pick your own — **$20 is a sensible starting point** |
| Advanced options | **Use unblended costs** |
| Alert threshold | 80% of actual cost, email to yourself |

**Choose unblended costs, not net unblended.** Net unblended subtracts your free-tier credits, so while credits are covering the bill the budget reads close to zero and never trips — exactly when you'd most want to know that something is burning money. Unblended tracks what you're actually consuming, credits or not.

You'll come back here after Step 4 to add the shutdown action, because the action has to point at an RDS instance that exists.

**On credits:** you don't need to configure anything. AWS applies free-tier credits to eligible charges automatically. The budget above is what tells you how fast you're spending them.

### Step 2 — Note your default VPC and subnets

**VPC → Your VPCs.** Note the default VPC ID, then under **Subnets** note two subnet IDs in different availability zones and the route table they're associated with.

You don't need to build anything — the default VPC is fine. You just need these IDs for later steps.

### Step 3 — Security groups

**EC2 → Security Groups → Create security group.** Create both before the resources that use them.

**`lambda-sg`** — for the Lambda function.

| Direction | Rule |
| --- | --- |
| Inbound | None |
| Outbound | Leave the default allow-all |

Lambda only makes outbound connections, so it needs no inbound rules at all.

**`db-sg`** — for RDS.

| Type | Port | Source |
| --- | --- | --- |
| PostgreSQL | 5432 | `lambda-sg` |
| PostgreSQL | 5432 | My IP |

The first rule is the important one: only the application can reach the database. The second lets you connect from your own machine to seed data and inspect tables with pgAdmin or DBeaver.

If your home IP changes, that second rule needs updating. That's normal, and it's a much better problem than leaving the port open.

### Step 4 — RDS PostgreSQL

**RDS → Databases → Create database.** Standard create.

| Setting | Value |
| --- | --- |
| Engine | PostgreSQL |
| Template | Free tier, or Dev/Test |
| DB instance class | `db.t3.micro` |
| Storage type | gp3 |
| Allocated storage | **20 GB** |
| Storage autoscaling | **Disabled** — uncheck "Enable storage autoscaling" |
| Maximum storage threshold | N/A once autoscaling is off |
| Multi-AZ | No |
| VPC | Default |
| Public access | **Yes** |
| VPC security group | `db-sg` (remove the default) |
| Automated backups | 0 days |
| Additional configuration → Initial database name | Set one |

Save the endpoint, port, master username, and password.

**Lock the storage at 20 GB and turn storage autoscaling off.** It is on by default, and it only ever grows — RDS will expand the volume on its own and never shrink it back, so a runaway seed script or a stray log table can quietly raise the monthly bill for the rest of the account's life. Twenty gigabytes is far more than any of these projects need. If you genuinely run out of space, that's worth knowing about, and you can raise it deliberately.

**Why "public access: yes" is still safe here.** That setting only decides whether the instance gets a publicly resolvable DNS name. The security group decides who may actually connect — and yours allows exactly two sources. From inside the VPC, the Lambda resolves that same hostname to a private address, so its traffic never leaves the VPC.

If you'd rather be stricter, set public access to **No** and drop the "My IP" rule. Everything still works, but you'll need to seed the database by invoking the Lambda rather than running the script from your own machine.

Set **Initial database name** — if you skip it, RDS creates an instance with no database in it, and the first connection fails in a confusing way.

### Step 4b — Attach the shutdown action to your budget

Now that the instance exists, go back to **Billing and Cost Management → Budgets**, open your budget, and add an action.

| Setting | Value |
| --- | --- |
| IAM role | Create one when prompted, so Budgets can act on your behalf |
| Action type | **Amazon RDS** |
| Instance | Your database instance |
| Operation | **Stop** |
| Threshold | Lower than your email alert — around 70% of the budget |
| Execution | Automatic |

Setting the action below the email threshold means the database stops before you'd otherwise be notified, which is the behaviour you want when nobody is watching.

Two things to be honest about. This is a **backstop, not a circuit breaker** — budgets evaluate against billing data that refreshes only a few times a day, so spend can overshoot before the action fires. And a stopped RDS instance **wakes itself after seven days**, at which point it bills again; the action won't necessarily fire a second time.

### Step 5 — S3 uploads bucket (private)

**S3 → Create bucket.**

| Setting | Value |
| --- | --- |
| Name | Globally unique, e.g. `yourname-medflow-uploads` |
| Block Public Access | **On** — leave all four boxes checked |
| Versioning | Disabled |

This holds the report attachments. It stays private; the backend generates presigned URLs rather than making objects public.

### Step 6 — S3 gateway endpoint

**VPC → Endpoints → Create endpoint.**

| Setting | Value |
| --- | --- |
| Service category | AWS services |
| Service | `com.amazonaws.<your-region>.s3` |
| Type | **Gateway** — not Interface |
| VPC | Default |
| Route tables | The one associated with your subnets from Step 2 |
| Policy | Full access |

This is what lets the VPC-attached Lambda reach S3. Without it, every boto3 call hangs until the function times out.

Two things to get right. **Type must be Gateway** — the Interface option also works but bills hourly per availability zone, while Gateway is free. And **the route table must be the one your Lambda's subnets actually use**, or the endpoint will exist, report as available, and do nothing.

Verify it by opening that route table: you should see a route to a `pl-` prefix list pointing at `vpce-…`.

### Step 7 — IAM execution role

**IAM → Roles → Create role.** Trusted entity **AWS service → Lambda**.

Attach:

- `AWSLambdaBasicExecutionRole` — writes logs to CloudWatch
- `AWSLambdaVPCAccessExecutionRole` — required for any VPC-attached function to manage its network interfaces
- An inline policy granting `s3:PutObject`, `s3:GetObject`, and `s3:DeleteObject` on `arn:aws:s3:::your-uploads-bucket/*`

Both managed policies are genuinely required. Without the VPC one the function can't start at all; without the basic one you get no logs, which makes everything afterwards much harder to diagnose.

Scope the inline policy to your one bucket rather than reaching for `AmazonS3FullAccess`.

### Step 8 — Package the backend

FastAPI runs on Lambda through the **Mangum** adapter, which translates Lambda events into ASGI calls:

```python
from mangum import Mangum
handler = Mangum(app, lifespan="off")
```

Build the deployment package **inside Docker**, using a Lambda-compatible Python base image such as `public.ecr.aws/lambda/python:3.12`. Installing dependencies directly on macOS or Windows produces binaries that won't load on Lambda — database drivers most of all. This is the most common reason a first Lambda deployment fails with an import error, and building in a container removes the problem rather than working around it.

Zip the installed dependencies together with your application code, keeping the handler module at the root of the archive.

### Step 9 — Lambda function

**Lambda → Create function.** Author from scratch.

| Setting | Value |
| --- | --- |
| Runtime | Python 3.12 |
| Architecture | Match what the Docker build produced |
| Execution role | Use existing — the role from Step 7 |

Then, under **Configuration**:

| Section | Value |
| --- | --- |
| General → Handler | `main.handler`, or wherever Mangum is assigned |
| General → Memory | 512 MB |
| General → Timeout | 30 seconds |
| VPC | Default VPC, your two subnets, security group `lambda-sg` |
| Environment variables | `DATABASE_URL`, `S3_BUCKET`, JWT secret, and anything else from `.env` |

Upload the zip from Step 8.

The default timeout is 3 seconds, which isn't enough for a cold start plus a database connection. Raising it isn't optional.

Run a test invocation and read the CloudWatch log stream before moving on. Confirming the function starts, imports cleanly, and reaches the database saves a great deal of guessing later.

> **CLI worth knowing:** re-uploading code is the step you'll repeat most.
> `aws lambda update-function-code --function-name <name> --zip-file fileb://package.zip`

### Step 10 — Function URL

**Lambda → your function → Configuration → Function URL → Create function URL.** Auth type **NONE**.

Leave the Function URL's own **CORS configuration empty** and let FastAPI's `CORSMiddleware` handle CORS. Configuring both produces duplicate `Access-Control-Allow-Origin` headers, which browsers reject — and the error points at CORS without hinting that the cause is having set it up twice.

Save the URL. It's the API base URL for the frontend.

### Step 11 — Create tables and seed

Point `bin/seed.sh` at the RDS endpoint and run it from your own machine, using the "My IP" rule from Step 3.

Tables need to exist before the API is useful, and triggering `create_all` from inside Lambda is fragile. Seeding locally against RDS is simpler and easy to repeat.

### Step 12 — S3 hosting bucket (private)

**S3 → Create bucket.**

| Setting | Value |
| --- | --- |
| Name | Globally unique, e.g. `yourname-medflow-web` |
| Block Public Access | **On** — all four boxes checked |
| Static website hosting | Leave **disabled** |

This bucket stays private. CloudFront reaches it through Origin Access Control, so there's no public bucket policy and no website endpoint.

### Step 13 — Build and upload the frontend

Set the production API base URL to the Function URL, run `npm run build`, and upload the contents of `dist/` to the hosting bucket.

The API URL is compiled into the build, so changing it means rebuilding — not just re-uploading.

> **CLI worth knowing:** `aws s3 sync dist/ s3://your-web-bucket --delete`
> Much less tedious than dragging files into the console on every change.

### Step 14 — CloudFront distribution

**CloudFront → Create distribution.**

| Setting | Value |
| --- | --- |
| Origin domain | Your hosting bucket — pick the **S3 bucket**, not a website endpoint |
| Origin access | Origin Access Control, then **Copy policy** and apply it to the bucket |
| Viewer protocol policy | Redirect HTTP to HTTPS |
| Default root object | `index.html` |
| Price class | The cheapest option covering your region |

Then under **Error pages**, add two custom error responses:

| HTTP error code | Response page path | HTTP response code |
| --- | --- | --- |
| 403 | `/index.html` | 200 |
| 404 | `/index.html` | 200 |

Those two entries are what make client-side routing work. Without them, refreshing on any route other than the root returns an error page. This catches nearly everyone the first time.

Don't skip applying the bucket policy CloudFront generates for you — the distribution can't read a private bucket without it.

The distribution's domain name is your live application URL.

### Step 15 — CORS, then the redeploy loop

Add the CloudFront domain to `allow_origins` in FastAPI's `CORSMiddleware`, alongside your local dev origin:

```python
allow_origins=[
    "http://localhost:5173",
    "https://d111111abcdef8.cloudfront.net",
]
```

Exact origins, no trailing slash, and drop the `*` wildcard once things work.

From here on, a frontend change means: rebuild, upload, **and create a CloudFront invalidation** on `/*`. Skipping the invalidation means serving the old build from cache and wondering why the fix didn't land.

> **CLI worth knowing:**
> `aws cloudfront create-invalidation --distribution-id <id> --paths "/*"`

---

## 6. Known Sharp Edges

- **Dependencies built outside Docker won't import.** Build in a Lambda-compatible container.
- **CORS configured twice** — on the Function URL and in FastAPI — fails in a way that looks like a CORS problem rather than a duplication problem.
- **A Gateway endpoint on the wrong route table** looks healthy and does nothing. S3 calls hang until the function times out.
- **Missing `AWSLambdaVPCAccessExecutionRole`** stops a VPC-attached function from starting at all.
- **Lambda caps request payloads at 6 MB.** Large uploads need presigned URLs so the browser sends files straight to S3.
- **Cold starts and connection pools don't mix well.** Create the engine at module level, outside the handler, and keep the pool small — or use `NullPool` and let each invocation open its own connection.
- **A stopped RDS instance restarts itself after seven days.**
- **Stale CloudFront cache** after any deploy without an invalidation.
- **A changed home IP** breaks the "My IP" rule on `db-sg`. Update the rule rather than widening it.

---

## 7. Cost Control

Lambda and CloudFront both have always-free monthly allowances this workload won't come close to exhausting. The gateway endpoint is free. RDS is the only meaningful spend.

- Stop the RDS instance when you're not working, remembering it wakes itself after seven days.
- The budget action from Step 4b is a safety net, not a substitute for stopping the instance yourself.
- Never create a NAT Gateway. Nothing here needs one.
- Delete everything after the showcase: the function, the RDS instance (skip the final snapshot), both buckets, and the distribution.
- Confirm current free-tier terms at [aws.amazon.com/free](https://aws.amazon.com/free) rather than assuming. Terms depend on the account's creation date, and accounts created after July 2025 receive credits rather than the older 12-month allowances.

---

## 8. Alternatives

Worth knowing about, and reasonable directions for anyone who finishes early.

**API Gateway in front of Lambda** — the conventional setup before Function URLs existed. Adds request validation, throttling, custom domains, and usage plans. More to configure, and unnecessary for a single service.

**Lambda container images** — package the app as a Docker image in ECR instead of a zip. Cleaner for large dependency trees and sidesteps the unzipped size limit, at the cost of an ECR repository to manage.

**AWS App Runner** — point it at a repository and it handles servers, scaling, and HTTPS. Less to configure than Lambda packaging, and no cold starts. The catch is no free tier and no automatic idling, so it bills continuously until deleted.

**Plain S3 website hosting without CloudFront** — fewer moving parts, but HTTP only and it requires a public bucket. Since an HTTP page may call an HTTPS API, it would work here — just without TLS on the frontend.

**NAT Gateway instead of the endpoint** — gives the VPC-attached Lambda general internet access rather than S3 only. Necessary if the application ever calls an external API, and roughly $32/month.

**Custom domain** — a Route 53 hosted zone plus an ACM certificate in us-east-1, attached to the distribution as an alternate domain name. The first real certificate work in this stack.

---

## 9. Definition of Done

- The CloudFront URL loads the application in a fresh browser.
- Deep links and page refreshes work on routes other than the root.
- Login succeeds and returns a token from the Function URL.
- The dashboard shows real numbers from RDS, not mock data.
- A file upload lands in the private bucket and the stored URL resolves.
- Each role behaves correctly through the deployed app, not just locally.
- CloudWatch shows logs for a real request.
- The RDS security group contains no rule wider than your own IP.
- The README records the CloudFront URL, the Function URL, and the deployment steps taken.