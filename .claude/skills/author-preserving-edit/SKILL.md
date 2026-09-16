---
name: author-preserving-edit
description: Revise existing technical academic prose (APS report, thesis chapter, paper draft, proposal) so it reads as the author's own writing, without altering any technical content. Use this when editing text that already exists and already carries evidence - measurements, failed experiments, design decisions, limitations, citations - rather than when drafting new text. Every measured value, evidence qualifier, decision chain and citation attachment survives the edit unchanged; only phrasing moves. Complements the academic-writing skill, which sets the register for new drafting; this skill governs what an editing pass is allowed to touch.
---

# Author-preserving editing

Drafting and revising are different jobs with different failure modes. The
`academic-writing` skill covers drafting: register, hedging, the phrases to
avoid, proposal conventions. Load it for the voice. This skill covers the
narrower and riskier job of rewriting prose that already exists and already
contains the author's evidence.

The risk being managed here is specific. A rewriting pass optimises for how
the sentence reads. Technical content lives in exactly the details a
readability pass treats as disposable: a reference datum in a prepositional
phrase, a modal verb, a subordinating "because", a qualifier that marks a
number as predicted rather than measured. Those survive a human editor
because the human knows what they are for. They do not survive an automated
paraphrase, and they do not survive a model told to "make this sound less
like AI" without being told what it is not allowed to lose.

So the contract is: phrasing is in scope, content is not.

## Absolute rules

**Never change a technical fact.** Measured values, units, dates, component
names, part numbers, control frequencies, dimensions, equations, parameter
symbols, percentages, error magnitudes, experimental conditions, acceptance
criteria, route lengths, sample counts, reference numbers, and which claim
each citation is attached to. If a fact looks wrong, say so in the change
report and leave the text alone. Flagging is allowed; silent correction is
not.

**Never change the evidence status of a claim.** Measured, calculated,
simulated, predicted, inferred, proposed, demonstrated, and not yet validated
are distinct states and the verb carries the distinction. "Predicted" does
not become "measured". "Proposed" does not become "demonstrated". "Appears
to" does not become "is". "Suggests" does not become "shows". Removing a
limitation because it weakens the paragraph is the same error in a different
place.

**Never remove a failure.** A controller that was replaced because it failed,
an estimator that performed worse than the simpler alternative, a coverage
criterion that was not met, a hardware approach abandoned after a measurement:
these are the contribution, not a blemish on it. They are also the single
strongest signal that the author did the work.

**Preserve the failure to evidence to decision chain.** When a design
decision followed from an observed failure, all three links stay in the text
and stay connected. Not "the system was changed to improve performance", but
what was observed, what it measured, and what was decided because of it. If
an edit would leave the decision without its cause, the edit is wrong.

**Never introduce a claim the source does not carry.** No new citations, no
new results, no novelty claims, no "state of the art", no "highly accurate",
no general superiority over methods that were never compared.

**Never change text inside a quoted title or a bibliography entry.** A
reference list holds titles as their publishers printed them. A consistency
check that flags "optimization" against a document written in British
spelling has found a citation, not an error. Same for hyphenation inside a
paper title. Leave them.

## What the humanizer actually does, and why it costs more than it returns

This section is the reverse-engineering, worked against a real sample: the
opening of Chapter 1 as HumanizeAI returned it. Each item is a class of
damage, with the change that produced it. Going sentence by sentence through
five paragraphs, the count came out at zero changes that improve the text,
two that are neutral, and a dozen that cost something. That ratio is the
whole argument.

**Reference data dropped from a measurement.** "rollers mounted at
forty-five degrees to the wheel axis" became "rollers mounted on it at forty
five degree angle". An angle without its datum is not a specification. This
is the worst single change in the sample, and it is in the sentence that
defines how the wheel works.

**A defining property deleted as redundant.** "without any change in wheel
orientation" is gone from the rewritten paragraph. That clause is the entire
reason mecanum drive answers the narrow-aisle problem rather than a steered
platform. The paraphrase kept the conclusion and removed the reason for it.

**Geometric characterisation replaced with a gesture.** "point-symmetric
rather than mirror-symmetric" became a loose dash clause. The precise term
was the content.

**Referent broken across a sentence boundary.** The original contrasts the
aisle against the wide routes automation was built around: "The aisle itself
has received far less attention." The rewrite says "The path itself, however,
has been largely overlooked", where "the path" now points back at the wide
paths of the previous sentence. The contrast the paragraph is built on
inverts.

**Scope widened.** "Mecanum kinematics alone do not solve the aisle problem"
became "The kinematics of mecanum wheels do not constitute a solution". A
bounded negative claim became an unbounded one, and the "because" clause that
justified it was severed into its own sentence.

**Modality softened.** "The chassis must then be wide enough" became "The
frame then should be large enough". A geometric necessity turned into a
recommendation. "Wide" turned into "large", which drops the one dimension the
entire chapter is about.

**Quantifier strengthened.** "relaxing the packaging constraint that sets
vehicle width" became "eliminates the packaging issue". The original was
careful. The rewrite overclaims and drops what was constrained.

**Terminology flattened.** "a human picker" became "a person walking through
it". Picking is the operation the aisle width is sized for; walking through
is not.

**Nominalisation added.** "machines that move goods along wide,
well-structured routes" became "the machinery of conveying materials on broad
and highly structured paths". Longer, vaguer, and precisely the construction
the style guidance says to remove.

**Orthography switched mid-document.** "centimetres" and "metres" came back
as "centimeters" and "meters", against a document that uses British spelling
throughout. Mixed orthography inside one report is itself a tell.

**Formulaic transitions inserted.** Three "however" openings appeared across
five paragraphs, and two dashes were added. Both are on the avoid list in the
same document that proposed the rewrite. The humanizer violated the style
rules it was supposed to be serving.

The pattern underneath all of these: a paraphrase engine reads a
prepositional phrase, a modal verb and a subordinate clause as optional
ornament. In technical prose they are where the specification lives.

## What to do instead

Edit for the things a rewrite can genuinely improve, and leave everything
else.

Formulaic paragraph openings are worth removing. "Furthermore", "Moreover",
"Additionally", "It is important to note that", "It should be noted that",
"This highlights the importance of". State the thing directly.

Noun-heavy constructions are worth unpacking. "The implementation of the
controller experienced a failure during rotation-only goal conditions" says
less than "The controller failed on rotation-only goals" and takes twice as
long to say it.

Sentence length is worth varying, but only where a real sentence boundary
belongs. Combine two sentences that carry one thought. Split one that carries
three. Move a qualification to the front or the back if that puts the main
clause where the reader needs it. Do not alternate short and long on a
schedule; that is as mechanical as uniformity and reads worse.

Active voice is worth using where the actor matters and the field's
convention allows it. Not everywhere. "Four runs were analysed" is correct as
it stands.

Terminological consistency beats lexical variety, every time. If the document
says "platform" forty-three times, it says "platform" forty-three times.
Cycling through platform, vehicle, machine and system to avoid repetition
tells a reader those are four different things. Keep mecanum, non-collinear,
inverse kinematics, wheel odometry, scan matching, pose graph, lidar,
feedforward, yaw rate, yaw-consistency residual, quadrature decoding,
costmap, acceptance criterion, and every part number exactly as they are.

Numbers stay as numbers. "The route closed to 19 mm over 8.00 m, 0.23 per
cent of path" is evidence. "The route showed very small positional error" is
an opinion about evidence that is no longer present.

## Paragraph patterns worth holding

Experimental prose reads best in a fixed order, and the order is also what
makes it verifiable: what was tested, why that one first, what was measured,
what happened, what it implies, what was decided. A worked example from this
project: the dynamic-window controller was tested first because it costs less
computation; it failed on rotation-only goals because the sampling procedure
rarely produced a candidate with exactly zero translational velocity; it was
replaced with a sampling-based predictive controller. Three facts, one causal
chain, no evaluative adjectives. Do not rewrite that into "the navigation
stack was refined for better performance".

A literature subsection should separate what is established, what the prior
work assumed, what it did not cover, and what that leaves open here. A
textbook summary of the field is not a review.

A limitation is stated, not managed. "The coverage criterion was not met
because the available test area did not provide a long enough traversable
loop" is a limitation. "Some scope remains for further optimisation" is an
evasion, and a committee reads it as one.

## Procedure

Work a paragraph at a time.

1. List the paragraph's factual claims and mark every number, unit, condition
   and citation. These are now frozen.
2. Mark each statement as observation, interpretation, prediction or
   conclusion. The marking constrains which verbs the rewrite may use.
3. Trace the causal links. Anything joined by "because", "so", "therefore" or
   "after" stays joined.
4. Identify the formulaic phrasing and the nominalisations. These are the
   edit targets.
5. Rewrite only those. If a sentence has no edit target, it does not get
   touched. Preferring the original is the default outcome, not a failure of
   the pass.
6. Diff the result against the source for meaning, not for wording: every
   frozen item present, every qualifier intact, every causal link intact, no
   claim widened, no modal softened or strengthened.
7. Check terminology and orthography against the rest of the document, with
   bibliography entries excluded from the check.

## Report the changes

Do not return revised text alone. Return the revised text, then the changes
made and why, then a list of what was deliberately left alone and the reason.
If anything in the source looked technically wrong, it goes in a separate
flagged list, unedited, for the author to decide.

## Self-check before returning

No numeric value, unit or condition altered. No evidence qualifier changed in
strength. No limitation or failed result removed or softened. No citation
moved to a different claim. No new claim or reference introduced. No
prepositional phrase carrying a datum dropped. No modal verb changed. No
bounded claim widened. Terminology consistent with the rest of the document.
Bibliography untouched. Orthography consistent outside the bibliography.
Sentence length varies because the content varies, not on a pattern.

## What this skill is not for

It is not a detector-evasion tool and it must not be turned into one. No rule
here targets perplexity, burstiness, GPTZero, Turnitin, or any classifier
score, and none should be added. Those objectives pull directly against the
ones above: the fastest way to move a classifier is to strip the specific
detail and add surface noise, which is the same operation as destroying the
evidence.

The honest position on detectors is that they disagree with each other,
change without notice, and misclassify genuine human writing at rates high
enough to be documented in the literature. No edit can promise a score. What
an edit can do is make the text read as the work of the person who ran the
experiments, and a report full of specific measurements, named failures and
documented decisions already reads that way before any stylistic pass runs.
Running such a report through a paraphrase engine trades the strongest
evidence of authorship for surface variation. That is a bad trade and this
skill exists to refuse it.
