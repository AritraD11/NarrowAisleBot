---
name: academic-writing
description: Apply calibrated, human-sounding academic and scientific prose to research proposals, papers, technical reports, and other formal long-form writing (Word, PDF, Markdown, or plain chat output). Use this whenever drafting or revising more than a paragraph of formal academic, scientific, or proposal text - grant proposals, literature reviews, methodology sections, technical reports, research write-ups. Rewrites away common AI-writing tells (stock phrases, uniform sentence rhythm, hedge-heavy filler, generic gap-statement templates, over-structured bullet lists) in favor of the register, precision, and voice of genuine academic writing. Defaults to the formal scientific/academic register; general-purpose human-writing rules apply underneath it.
---

# Academic writing

Write like a researcher who knows this material and is drafting the proposal or paper themselves, not like a model completing a prompt. This skill defaults to the formal academic and scientific register: no contractions, calibrated hedging, precise terminology, passive voice where the convention actually calls for it. The general rules below are the base layer; where they conflict with the academic-register rules further down, the academic rules win.

## Before writing

Pick the one or two points that actually matter and lead with them. Don't hedge every sentence or cover every angle just because it's possible to - a document that says one thing clearly reads as more human than one that qualifies everything. In a proposal or paper this usually means: state the gap, state what the work will do about it, then support both with specifics, not adjectives.

## Cut these words and phrases

delve, tapestry, landscape (used metaphorically), realm, underscore, boast, testament to, underpinnings, navigate (used metaphorically), tackle (used metaphorically), leverage (as a verb meaning "use"), utilize, spearhead, streamline, empower, foster, harness, seamless, cutting-edge, game-changer, unlock, elevate, pivotal, innovative, groundbreaking, transformative, unprecedented, paradigm shift, holistic, synergy, multifaceted, ever-evolving, future-ready, in today's [X] world, it's important to note that, it's worth noting, notably (as a sentence opener), at the end of the day, when it comes to, plays a crucial/vital role, dive into / deep dive, look no further, it goes without saying, needless to say, to recap.

Exception: keep a word from this list when it's the actual technical term for something, not filler. "Robust optimization" is a named subfield, not padding, so it stays in a document about robust optimization. The ban is on reflexive use ("a robust solution" applied to nothing in particular), not on correct technical vocabulary.

Also cut: the em dash used as a dramatic pause. Use a comma, period, or parenthesis instead.

## Cut these structures

- An opening paragraph that previews what the document is about to cover, or a closing one that restates it ("In summary, X is a multifaceted topic that..."). Start on the actual first point and end on the actual last one.
- "It's not just X, it's Y."
- Rule-of-three lists reached for out of habit ("clarity, consistency, and confidence") rather than because there are really three things.
- Perfectly balanced "on one hand / on the other hand" framing when nobody asked for balance and the document is supposed to land on a conclusion.
- Headers and bullets applied by default. Use a list only when the content actually is one - steps, options, a spec sheet - not as scaffolding for an explanation that would read better as connected paragraphs.
- The "**Bold term:** explanation" list format as a substitute for actual paragraphs. It's a recognizable template, not writing.
- Uniform rhythm at any level: every sentence the same length, every paragraph the same length, every section given equal depth regardless of how much the point actually needs.
- Mixing modal/tense conventions for the same kind of claim within one document - "shall be conducted" in one paragraph, "is conducted" in the next, "will be conducted" in a third. Pick one and hold it for the whole section (see Tense discipline below).

## Do this instead

- Vary sentence length on purpose. A short sentence placed after two longer ones carries more weight than any banned phrase above could.
- Use specific numbers, names, and examples instead of general claims. "Cut setup time from three hours to one" beats "significantly improved efficiency."
- Take a position when the document calls for a recommendation or a finding, rather than surveying every side of it.
- Let sentences connect the way people actually talk: with "and," "so," "but," or nothing at all, not "furthermore" or "moreover" every time.
- Use contractions unless the document's register is genuinely formal (a legal filing, not a project report).
- Keep domain terminology exactly as a practitioner would use it. Don't over-explain basics to an audience that already knows them just to pad length.

## Academic and scientific register

This is the default register for this skill: a paper, a thesis chapter, a grant proposal, or a technical report headed for an academic or scientific reviewer. Apply these on top of the general rules above:

- Drop contractions entirely.
- Don't cut hedging, calibrate it. "The results suggest," "indicate," and "demonstrate" claim different strengths of evidence, and the correct one is whichever the data actually supports. Overclaiming certainty is a correctness problem in science, not just a style one - this is the one register where hedging is often the honest choice, not filler. Hedge on what's genuinely unproven (a proposal's central hypothesis, an untested integration), not on established background facts.
- Skip rhetorical questions, humor, and asides dropped into prose for rhythm. This is different from a problem statement ending on direct, numbered research questions ("Does a fused model combining two- and three-dimensional gait, cardiopulmonary vitals, and thermal data outperform any single modality on an active warehouse floor?") - that's a standard, legitimate proposal convention, not a rhetorical aside.
- Reserve "significant" and "significantly" for actual statistical significance (a named test, a stated threshold). Never use them as a synonym for "notable" or "large" - that specific misuse is one of the most checkable tells in generated scientific writing.

Academic-specific tells to also cut:

- The gap-filling template: "Previous studies have examined X. However, few have addressed Y. This study aims to..." Formulaic regardless of who writes it, but disproportionately common in generated literature reviews. Ground the gap in specific, named prior work instead - see Naming the gap below for a worked example.
- Every section built to identical length and internal structure, independent of how much each part actually needs.
- Results reported only in general terms ("improvements were observed across all metrics") instead of the actual numbers.
- Citation strings with no synthesis: (Smith 2020; Lee 2021; Kumar 2022), where the sentence never says what's different between what each one found.
- Passive voice used by default to sound more formal, past where it's the field's real convention (methods sections, mainly). Where active voice states it more clearly, use active voice.

## Proposal-specific conventions

Grant and funding proposals are their own register within academic writing: they describe work that hasn't happened yet, they're read by reviewers skimming dozens of submissions, and every rupee or hour has to be defended. These conventions are drawn from proposals that were actually drafted, reviewed, and submitted through this skill.

**Tense discipline marks what already exists versus what the project will do.** Motivation and problem framing, what's true today, sit in present tense: "Two approaches to fatigue detection exist today, and neither scales to this environment." Methodology, deliverables, and anything the project will produce sit in future tense, consistently, for the entire section: "will perform," "will capture," "will measure," "will be validated." A proposal is a plan, not a report of finished work - don't drift into present tense mid-methodology because a sentence happens to sound more confident that way. Biography and track record sit in past or present-perfect: "has served as a Professor since 2022," "has published more than 50 papers." Re-read each section on its own and check the tense never drifts within it - this is one of the easiest things to lose across multiple editing passes.

**A short bolded lead-in beats a subheading for a paragraph-sized point.** "Privacy by design.", "Evaluation.", "A tiered sensing ladder, not one fixed rig." - a label as a sentence fragment, a period, then the point developed in prose underneath. This reads as a person structuring an argument, not a template with a heading over every idea. Reserve it for genuine pivots in the argument, not every paragraph.

**A vague claim is a placeholder for a specific one.** "Fails under Indian warehouse conditions" is an assertion. "Fails under Indian warehouse conditions for well-documented reasons: discomfort above 40°C, signal degradation from perspiration, low worker compliance, and the daily burden of charging thousands of devices" is evidence. If a sentence would survive being pasted unchanged into an unrelated proposal, it hasn't earned its place yet.

**Naming the gap: state it against specific prior work, not a generic shortage of studies.** Not "few studies have examined X." Instead: "Existing multimodal systems are built either for driver drowsiness, combining a facial camera with EEG, or for controlled biomechanics laboratories, where subjects are instrumented with sEMG and IMU bands; the integration of vision, LiDAR, radar, and thermal imaging specifically for industrial fatigue remains untested." Name what exists first, then show precisely what it doesn't cover.

**Every number is attached to something, not floating.** Cost justification and results prose are the easiest places for this to slip - a total with no line-item reasoning, an accuracy claim with no baseline, both read as generated. Tie every figure to the specific thing it measures or buys: "under 10% gait error, above 90% vital-sign correlation, and within 0.5°C of thermal reference readings," not "high accuracy across all sensors."

**Section and objective headings should be readable on their own.** A reviewer skimming only the titles should be able to say what each part does. "Objective 1: Sensor Integration" tells them nothing; "Objective 1: Integration of a Co-located Multi-Sensor Edge Node for Contactless Fatigue Detection" does.

**Terminology precision over near-synonyms.** A camera measures temperature; it doesn't read it. Match the verb to what the instrument or method actually, physically does - a domain-expert reviewer catches a loose verb before they catch anything else.

**Watch subject-verb agreement around "neither," "each," and collective nouns.** These are exactly where the ear loses track of the real subject in a long sentence ("neither... scale" instead of the correct "neither... scales"), and exactly the kind of error that survives several editing passes because it reads fine at a skim. Worth a dedicated slow re-read on any sentence with a buried singular subject.

## Why these rules work, briefly

Detectors lean heavily on two proxies: how predictable the word choices are (perplexity) and how much sentence rhythm varies across the text (burstiness). AI text tends toward the most probable next word and an even rhythm; the rules above push against both. That's a simplification, not a confirmed account of how any specific detector works internally, since most of them are undisclosed classifiers. Treat it as a reasonable working model for why the rules help, not as settled fact.

## Before finalizing, check

1. Read it back. Would a colleague reading this guess it was drafted by AI? If any phrase from the cut list survived, and isn't doing genuine technical work, remove it.
2. Do all the paragraphs, or sections, look the same shape and length as each other? Break that up.
3. Pick one sentence at random. Could it be pasted into a hundred other reports on other topics unchanged? If yes, make it specific to this one.
4. Does the opening preview the document, or the ending restate it? Cut whichever one does.
5. Is "significant" reserved for actual statistical significance? Is every hedge calibrated to what the evidence supports, rather than stripped out for false confidence, or piled on as filler?
6. Does tense stay consistent within each section - future throughout methodology and deliverables, present throughout motivation, past or present-perfect throughout biography - with no drift introduced by a later editing pass?
7. Does every in-text citation correspond to the specific claim next to it, and does every entry in the reference list get cited at least once? A stale citation left over from a renumbering is one of the easiest errors to miss and one of the fastest for a reviewer to catch.

## What this does not do

This makes writing sound like a person wrote it. It doesn't, and can't, guarantee a specific score on any particular AI-detection tool. Detectors disagree with each other, change often, and, per published research, flag plenty of genuinely human writing too, especially writing with simpler sentence structure or a smaller vocabulary range. Treat "reads like a person wrote it" as the real target, not "beats detector X this week."
