# Vision — the narrow-aisle thesis, the Indian market, and the path to a company

**Written 28 Aug 2026.** This is a strategy document, not a business plan. Its
job is to say what this robot could become, why the geometry is the asset, and
what the honest risks are.

> **A rule this document keeps.** Every market *number* is marked
> **[SOURCE REQUIRED]**. Structural arguments and technical claims are made
> directly; sizing figures are not, because a figure cited from memory in a
> report is worse than no figure. §12 lists exactly what to look up and where.

---

## 1. The thesis, in one sentence

> **Indian warehouse and retail-backroom space is expensive and getting more
> so, Indian labour is not — so the robot that wins here is not the one that
> replaces a worker, it is the one that lets the same floor hold more
> inventory. That is a *geometry* problem, and this robot is 250 mm wide.**

Everything else in this document follows from that sentence.

---

## 2. Why the usual AMR pitch does not work in India

Almost every mobile-robot company pitches **labour arbitrage**: the robot costs
less per year than the people it replaces. That maths is compelling in a market
with expensive warehouse labour. **It is weak in India, and pretending
otherwise is how a hardware startup dies with a great demo.**

The three pitches that *do* work here, in order of strength:

### 2.1 Space (the strong one)

Rack aisles exist for the *vehicle*, not the goods. Aisle width is dictated by
whatever must drive down it — a person with a trolley, a pallet jack, a forklift.

Shrink the vehicle and you can shrink the aisle. Shrink the aisle and the same
floor holds more racking. **Rent is a monthly cost that never stops; the robot
is bought once.** In dense urban locations — precisely where quick-commerce
dark stores are — that arithmetic is very strong.

**This is the pitch that fits a 1000 × 250 mm robot, and it is the only pitch
where its odd shape is an advantage rather than a limitation.**

### 2.2 Error rate and traceability

Mispicks, misplacements and shrinkage cost real money in pharma, spares and
electronics distribution. A robot that logs every movement gives an audit trail
a human trolley does not. In regulated categories (pharma), traceability is
not a nice-to-have.

### 2.3 Throughput consistency

Not "faster than a human" — humans are fast. **Consistent**: the same cycle
time at 3 a.m. as at 3 p.m., during a festival-season peak, without training a
seasonal hire.

---

## 3. The geometry, stated as a product claim

| | Typical mecanum AMR | **NarrowAisleBot** |
|---|---|---|
| Footprint | roughly square | **1000 × 250 mm** |
| Aspect ratio | ~1:1 | **4:1** |
| Wheelbase | symmetric | **asymmetric, l₁ − l₂ = 70 mm** |
| Turns in place | yes, but sweeps a large circle | yes, and **strafes without turning at all** |
| Aisle it fits | wide | **under 350 mm clear** |

Square robots are square because symmetric kinematics are easy to control. The
long, narrow, asymmetric form is harder — every controller path must carry two
lever arms instead of one, and this project has the bug history to prove it —
**and that difficulty is exactly why the shape is uncontested.**

Two honest constraints that must be stated in any pitch:

- **It is a tote and carton mover, not a pallet mover.** At 250 mm wide it
  carries small-to-medium items along its 1 m length. Do not let anyone imagine
  a forklift replacement.
- **It moves goods; it does not pick them.** Picking from a shelf is a
  manipulation problem an order of magnitude harder. The near-term product is
  transport-and-present, with a human doing the hand movement.

---

## 4. Who actually pays, ranked by ease of entry

### Tier 1 — go here first

**Quick-commerce dark stores.** The sharpest fit in the Indian market, and the
reasoning is structural:

- They are **small** (a few thousand square feet) and in **expensive urban
  locations**, so density is the operator's central obsession.
- Aisles are already narrow because rent forced them to be.
- The category is **new**, so there is no legacy automation to displace and no
  twenty-year-old WMS to integrate with.
- Operators are **well-capitalised and pilot-friendly** — they run experiments
  as a matter of course.
- Layouts are **standardised across hundreds of stores**, so one successful
  pilot is a repeatable template rather than a bespoke project. **This is the
  single most important property.**

**Pharma distribution.** Dense small-SKU shelving, high unit value, regulated
traceability, and existing tolerance for capex. Slower sales cycle, higher
willingness to pay.

### Tier 2 — real, harder

- **Auto spare-parts distribution.** Enormous SKU counts, dense shelving, poor
  digitisation. Very fragmented buyer base.
- **Textile and garment warehousing.** High density, high labour intensity,
  price-sensitive.
- **Electronics and component distribution.** Small, valuable, dense.

### Tier 3 — the long-term vision, not the wedge

- **Hospital logistics.** Linen, samples, meals, pharmacy runs. Corridors are
  generally wide, so the narrow form is not the differentiator; safety
  certification around patients is a serious barrier.
- **Restaurant and food service** — the food-delivery cart in the journal's
  §1.4. Emotionally compelling, commercially harder: low margins, hostile
  environment (spills, crowds, children), and the buyer is the least
  automation-ready in this list.

> **The food-delivery cart and the warehouse robot are different companies.**
> Same chassis, different buyer, different sales motion, different regulation.
> Pick one to sell and let the other stay a demo. The demo is genuinely useful
> for raising money and attention — just do not let it set the roadmap.

---

## 5. The wedge — the smallest sellable thing

Do **not** try to sell "an autonomous mobile robot." Sell one measurable job:

> **"Replenishment runs in a dark store: the robot carries a tote from goods-in
> to the aisle face and waits, so the picker never walks the length of the
> store empty-handed."**

Why this specific job:

- It needs **transport**, which this robot does, and **no manipulation**,
  which it does not.
- It is measurable in the operator's own existing metric — picks per hour.
- It fails gracefully. If the robot stops, a human picks up the tote and walks.
  **Nothing in the store breaks.** For a first deployment that property is
  worth more than any feature.
- It needs **one** robot to prove, not a fleet.

---

## 6. Product ladder

| Stage | What it is | Gate to reach it |
|---|---|---|
| **0 — today** | A research platform that maps, plans and reaches goals | Autonomy chain 12/13 links working |
| **1 — Sept 2026** | Point-and-go on a saved map, named locations, phone UI | **This week's plan** |
| **2** | One robot doing one repeated job in a real space for a week, unattended | Reliability, battery management, docking |
| **3** | Fleet of 3–5, a task queue, a WMS-facing API | Multi-robot coordination, traffic |
| **4** | Product: install in a new store in a day, remote monitoring, SLAs | Commissioning tooling — the map is the install |
| **5** | Adjacent form factors on the same stack | Platform |

**Stage 2 is the real chasm.** "Works when watched" to "works unattended for a
week" is where most robotics projects stop, and it is almost entirely about
failure recovery, not autonomy: what happens when it gets stuck, loses
localisation, runs low on battery, or someone leaves a carton in the aisle.

---

## 7. Why now

| Force | Why it helps |
|---|---|
| **Quick commerce** | An entirely new dense-urban store format built in the last few years, still figuring out its operations. **[SOURCE REQUIRED]** for store counts and growth |
| **Grade-A warehousing growth** | Institutional-quality warehousing means standardised layouts, which automation needs. **[SOURCE REQUIRED]** |
| **Urban land cost** | The whole space argument. **[SOURCE REQUIRED]** for the rent trend |
| **Component cost collapse** | ESP32-class MCUs, 2D LiDAR and SBCs are now commodity. A capable base costs a fraction of what it did five years ago |
| **Open-source stack maturity** | ROS 2 + Nav2 + slam_toolbox is production-grade and free. **The corollary matters: none of it is a moat** |
| **Domestic manufacturing incentives** | Local assembly avoids import duty on finished robots and suits public-procurement preferences. **[SOURCE REQUIRED]** for current scheme details |

---

## 8. Competition, and where the gap is

The Indian mobile-robotics landscape is real and non-trivial. Well-known
players include **GreyOrange**, **Addverb Technologies**, **Ati Motors**, and
**Unbox Robotics**, alongside imported Chinese systems (Geek+, Hai Robotics
class). **[SOURCE REQUIRED]** — verify each company's current positioning
before writing any of this in a report; do not cite it from memory.

The structural observation, which does not depend on those details:

- **Goods-to-person shelf-carrying robots** (the Kiva pattern) require racks
  designed for robots and a large capital commitment. They serve big
  fulfilment centres.
- **Industrial AMR tugs** are built for factory floors and wide aisles.
- **Sortation robots** solve a different problem entirely.

**None of them are 250 mm wide.** The gap is small-format, dense, existing
spaces that were never designed for automation — where the constraint is
physical width and the buyer cannot rebuild the store.

### 8.1 What is actually defensible

Be ruthless here, because it is the question every investor asks:

| Candidate moat | Honest verdict |
|---|---|
| SLAM / navigation | ❌ **None.** It is open source. Everyone has it |
| The asymmetric kinematics | 🟡 Small. Real engineering, replicable in a month by someone competent |
| **The form factor + the fact that it works in <350 mm** | 🟢 **Real but temporary.** A physical constraint competitors would need to redesign around, not patch |
| **Cost, via an Indian BOM and Indian assembly** | 🟢 **Real and durable** if genuinely achieved. Hard to copy from a high-cost base |
| **Operational software: fleet, tasks, WMS integration, remote diagnostics** | 🟢 **The eventual moat.** Boring, unglamorous, and where the switching cost lives |
| Deployment speed — install in a day | 🟢 Underrated. If commissioning takes a week of engineers, the business does not scale |

**Read that table honestly: the moat is not the robot. The moat is cost plus
the software that makes a hundred of them manageable.** The narrow form factor
is what gets the first door open.

---

## 9. Unit economics — the skeleton to fill in

Do not guess these. Build the table from actual quotes.

| Line | How to get it |
|---|---|
| BOM (chassis, 4 motors + drivers, mecanum wheels, Pi 5, ESP32, LiDAR, battery, level shifters, frame) | **You have this robot. Add up the actual invoices.** This is the one number available today at zero cost |
| Assembly + test labour | Hours × rate, measured on the next build |
| Landed cost | BOM + assembly + 15–25% for spares, fixtures, failures |
| Price | Cost ÷ (1 − target gross margin). Hardware needs 40–55% gross to survive |
| Customer payback | Price ÷ (monthly rent saved + error reduction + throughput) |

**The number that decides the business:** payback period. Under 18 months and
operations will champion it internally. Over 36 and it needs a CFO's approval,
which is a different and much slower sale.

**Do this before September 30.** Adding up the invoices for the robot already
built is a one-evening task, and a report containing a real BOM cost is
enormously more credible than one containing a projection.

---

## 10. What kills this — the honest list

| Risk | Severity | Mitigation |
|---|---|---|
| **Hardware startups are capital-hungry and slow** | 🔴 | Stay at one robot until one customer has paid for one job |
| **The demo-to-product chasm (Stage 2)** | 🔴 | Treat failure recovery as the product from day one, not as polish |
| **250 mm is too narrow to be useful** | 🔴 | **Test this before building anything.** Go measure real dark-store aisles and ask what actually moves down them. If the answer is "pallets", the thesis is wrong |
| **Safety and liability around people** | 🟠 | The `collision_monitor` chain already exists. Certification is a real cost — budget for it, do not discover it |
| **A well-funded incumbent builds a narrow variant** | 🟠 | Speed, and the operational software moat |
| **Chinese imports undercut on price** | 🟠 | Local support and integration; a robot with no service network is unsellable in a warehouse |
| **Solo founder, hardware, no ops co-founder** | 🟠 | Find someone who has run a warehouse. Not a roboticist — this project does not need a second roboticist |
| **The SLAM problem never gets solved** | 🟡 | It will; it is localised to a parameter family. But do not raise money before it is |

**The third row is the one to act on first, and it costs nothing.** A tape
measure, three real sites, and one afternoon of asking "what moves down this
aisle, and how wide is it?" either validates the entire thesis or kills it
before a rupee is spent. **Do that before writing another line of navigation
code for commercial reasons.** (Keep writing it for APS — that deadline is real
and independent.)

---

## 11. The 18-month path, if it is pursued

| When | Milestone | What it proves |
|---|---|---|
| **Sept 2026** | APS report; point-and-go working; recorded demo | The technology is real |
| **Oct–Nov 2026** | 3 site visits with a tape measure; 10 operator conversations | **The thesis is real, or it is not** |
| **Dec 2026** | Real BOM cost; a payback model built on measured numbers | The economics are real |
| **Jan–Mar 2027** | Robot v2: docking, battery management, unattended for a week | Stage 2 crossed |
| **Apr–Jun 2027** | One unpaid pilot in one real store, instrumented | Someone wants it |
| **Jul–Sep 2027** | One **paid** pilot; a second robot; a fleet dashboard | Someone will pay |
| **Oct 2027** | Seed raise, or a decision to stay a research project | — |

**The honest branch point is at "one paid pilot."** If a real operator will not
pay for a second robot after seeing the first, the thesis is wrong, and finding
that out in 2027 for the cost of a pilot is a very good outcome compared with
finding out in 2029 after a raise.

---

## 12. Numbers to source before citing any of this

Every **[SOURCE REQUIRED]** above resolves to one of these. Look them up, write
down the source and the date, and cite them properly.

| # | What | Where to look |
|---|---|---|
| 1 | Indian warehousing stock and Grade-A share; absorption trend | Commercial real-estate research (JLL, CBRE, Knight Frank India) |
| 2 | Warehouse rent per sq ft, metro vs periphery | Same |
| 3 | Quick-commerce dark-store counts and growth | Listed-company investor decks and quarterly results |
| 4 | **Actual aisle widths in real dark stores** | **A tape measure. This one you measure yourself, and it is the most valuable number in the list** |
| 5 | Warehouse labour cost per shift by region | Industry surveys, staffing firms |
| 6 | AMR market size, India | Analyst reports — treat with scepticism; these are frequently inflated |
| 7 | Competitor positioning and funding | Company sites, press, filings |
| 8 | Import duty on finished robots vs components; current manufacturing incentives | Customs tariff schedule; scheme documents |
| 9 | Safety standards applicable to AMRs in Indian workplaces | Standards bodies; ISO 3691-4 as the international reference |

**Item 4 is the whole thesis in one measurement.** If real aisles are 900 mm,
a 250 mm robot has no advantage over a 600 mm one and the differentiation
evaporates. If they are 400 mm, almost nothing else on the market fits.

---

## 13. The vision, stated plainly

Strip away the market analysis and here is what this is:

> **Indian cities are running out of cheap floor space, and everything people
> buy has to sit on some of it before it reaches them. The robots built to
> move that inventory were designed for American and Chinese warehouses —
> wide, square, purpose-built. Indian dense-retail space is none of those
> things.**
>
> **NarrowAisleBot is a robot shaped like the aisle, not like the warehouse.
> A metre long, a quarter-metre wide, that slides sideways down a gap a person
> cannot walk through with a box in their hands.**
>
> **If it works, the unit of value isn't a replaced worker. It's a rack that
> fits where a walkway used to be.**

That is a thesis a reviewer or an investor can hold in their head. It is
falsifiable — item 4 above falsifies it in an afternoon. And it is the one
story where the strange shape of this robot is the *point* rather than a
compromise.

---

## 14. What to do this month, at zero cost

1. **Finish the autonomy demo.** Nothing here matters without it, and the APS
   deadline is real and independent of any of this.
2. **Add up the invoices.** Real BOM cost. One evening.
3. **Measure three real aisles.** Any dark store, any pharma distributor, any
   spares warehouse. Tape measure. Photograph each one with the tape in frame.
4. **Ask five operators one question:** *"What moves down this aisle, and what
   is the most annoying part of moving it?"* Write down the answers verbatim,
   not your interpretation of them.
5. **Do not incorporate anything, do not raise anything, do not build a second
   robot.** Not yet. The information from steps 2–4 changes what the second
   robot should be.
