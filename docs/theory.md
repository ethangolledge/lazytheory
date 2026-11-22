# Music theory, from physics up

This is the domain knowledge the code models. It starts from physics, derives what it can with
mathematics, and keeps naming and cultural choices separate from both.

Each claim is tagged with one of three labels:

| Tag | Meaning | In code |
|---|---|---|
| **[physics]** | Measurable property of sound or hearing | Fixed behaviour |
| **[math]** | Follows exactly from definitions | Fixed behaviour |
| **[convention]** | A human choice: names, standards, style | Swappable data |

When something is unclear, the rule is: if it isn't physics or math, it's data that can be
swapped out.

---

## 1. Sound and pitch

**[physics]** A pitched sound is a periodic vibration. Its repetition rate is the
*fundamental frequency* `f`, measured in Hz.

**[physics]** An ideal vibrating string or air column also vibrates at whole-number multiples of
`f`: `f, 2f, 3f, 4f, …`. These are the *harmonic series* (also called *partials* or *overtones*).
A string's fundamental is `f = (1 / 2L) · √(T / μ)` (Mersenne's laws), where `L` is length,
`T` is tension and `μ` is mass per unit length.

**[physics]** Real instruments only approximate this. Stiff strings (piano, bass) have partials
slightly sharp of whole multiples (*inharmonicity*), which is why pianos are "stretch tuned".
Bells, drums and bars have partials that aren't near whole multiples at all.

**[physics]** Over the musical range, pitch is heard roughly in proportion to the *logarithm* of
frequency. Equal *ratios* sound like equal *distances*. 100→200 Hz sounds like the same jump as
200→400 Hz.

**[physics]** Below roughly 20 Hz, a periodic event is heard as separate pulses (rhythm), not as a
pitch. Rhythm and pitch are the same thing at different speeds (see §10).

## 2. Intervals are ratios

**[math]** An *interval* is the ratio between two frequencies. Because hearing is logarithmic,
intervals are measured on a log scale. The standard unit is the *cent*:

```
cents(r) = 1200 · log2(r)
```

Intervals then *add* where ratios *multiply*: `cents(a·b) = cents(a) + cents(b)`.

**[physics]** The *octave* (2:1) is the simplest interval after unison. Every partial of the upper
note is also a partial of the lower one.

**[convention]** Hearing tones an octave apart as "the same note" (*octave equivalence*) is strong
in Western listeners, especially musicians, but was not detected in Tsimane' listeners in the
Bolivian Amazon (Jacoby et al. 2019). Scales repeating every octave is therefore a choice built on
the physics, not a law. The code treats the period as a parameter.

**[math]** The ratios between neighbouring harmonics give the simple intervals:

| Harmonics | Ratio | Cents | Common name |
|---|---|---|---|
| 2:1 | 2/1 | 1200.000 | octave |
| 3:2 | 3/2 | 701.955 | perfect fifth |
| 4:3 | 4/3 | 498.045 | perfect fourth |
| 5:4 | 5/4 | 386.314 | major third |
| 6:5 | 6/5 | 315.641 | minor third |
| 7:4 | 7/4 | 968.826 | harmonic seventh |

**[physics]** Two measurable properties separate simple-ratio intervals from complex ones:

- *Roughness.* Partials that are close but not equal *beat* (Helmholtz; Plomp & Levelt 1965).
  Simple ratios line up many partials exactly, so they beat less. This depends on timbre: with
  inharmonic timbres, other intervals beat least (Sethares, *Tuning, Timbre, Spectrum, Scale*).
- *Harmonicity.* How closely the combined partials fit a single harmonic series. Across 250+
  Western listeners, this predicted preference for consonant chords; aversion to beating did not
  (McDermott, Lehr & Oxenham 2010). Reanalysing 500+ listeners and 100,000+ pieces, Harrison &
  Pearce (2020) found consonance is a composite of roughness, harmonicity and familiarity.
- Harmonicity depends mostly on the pitch classes; roughness depends on the voicing, because
  the critical band within which partials beat is wider at low frequencies (§7).

**[convention]** *Preferring* consonance is learned. Tsimane' listeners told consonant and
dissonant chords apart but rated them equally pleasant (McDermott et al. 2016). The code can
compute roughness or harmonicity; it must never rank intervals as "good" or "bad".

## 3. Why 12 notes? Temperament

**[math]** Stacking pure fifths (3/2) never lands exactly on an octave (2/1), because no power of
3 is a power of 2. A *temperament* is a compromise: a finite set of steps per octave that
approximates the useful ratios well.

**[math]** How well an *N*-step equal division approximates the fifth comes from the continued
fraction of `log2(3/2) = 0.58496…`. Its convergents are

```
1/2, 3/5, 7/12, 24/41, 31/53, 179/306, …
```

So 5, 12, 41 and 53 steps per octave contain unusually good fifths. Twelve is the smallest that
also gets thirds roughly right.

**[math]** *12-tone equal temperament (12-TET or 12-EDO)* divides the octave into 12 equal steps
(*semitones*) of ratio `2^(1/12)`, i.e. 100 cents each:

```
f(s) = f_ref · 2^(s / 12)        s = number of steps from the reference
```

**[math]** The cost: only the octave is pure. Compared with pure ratios:

| Steps | 12-TET cents | Nearest simple ratio | Pure cents | Error |
|---|---|---|---|---|
| 0 | 0 | 1/1 | 0.000 | 0.00 |
| 1 | 100 | 16/15 | 111.731 | −11.73 |
| 2 | 200 | 9/8 | 203.910 | −3.91 |
| 3 | 300 | 6/5 | 315.641 | −15.64 |
| 4 | 400 | 5/4 | 386.314 | +13.69 |
| 5 | 500 | 4/3 | 498.045 | +1.96 |
| 6 | 600 | 45/32 *(ambiguous)* | 590.224 | +9.78 |
| 7 | 700 | 3/2 | 701.955 | −1.96 |
| 8 | 800 | 8/5 | 813.686 | −13.69 |
| 9 | 900 | 5/3 | 884.359 | +15.64 |
| 10 | 1000 | 16/9 or 9/5 or 7/4 *(ambiguous)* | 996.090 / 1017.596 / 968.826 | — |
| 11 | 1100 | 15/8 | 1088.269 | +11.73 |
| 12 | 1200 | 2/1 | 1200.000 | 0.00 |

**[math]** Which ratio a tempered step "means" is not always unique (6 and 10 above). The code
should allow several candidate ratios for one step, not a single lookup.

**[math]** Two well-known discrepancies that temperaments distribute:

- *Pythagorean comma*: 12 fifths vs 7 octaves, `3¹² / 2¹⁹` ≈ 23.46 cents.
- *Syntonic comma*: four fifths vs a major third two octaves up, `81/80` ≈ 21.51 cents.

**[convention]** 12-TET is the current Western default. Other systems are equally valid inputs:
other equal divisions (19, 24, 31, 53 …), *just intonation* (exact ratios), historical
temperaments, non-octave systems (e.g. Bohlen–Pierce divides 3:1). Microtones mean using a
different system, not a special case of 12.

## 4. Steps, pitch classes and the relative model

**[math]** Within an *N*-step system, a pitch is an integer number of steps from a reference.
Octave equivalence makes pitches *mod N* the same *pitch class*. For 12-TET, `0..11`.

**[math]** Everything musical is *relative*. Measure every pitch from a chosen *root*
(root = 0). An interval is a difference in steps, and transposing is adding a constant mod N.
Absolute frequency only appears at the end, when a root is attached to a reference pitch.

**[convention]** The reference pitch (A4 = 440 Hz, ISO 16) and the letter names (C, D, E …) are
labels for absolute positions. They sit on top of the relative model; nothing below depends on
them.

**[convention]** Interval *names* ("minor third", "♭3", "perfect fifth") are labels for step
counts (3, 3, 7 in 12-TET), with distinctions inherited from the diatonic scale (§5). Step counts
are what the code stores; names are lookups.

## 5. Scales

**[math]** A *scale* is a set of pitch classes containing the root, e.g. `{0, 2, 4, 5, 7, 9, 11}`.
It can also be written as its *step pattern*, the gaps between neighbours, which always sum to N:
`2 2 1 2 2 2 1`.

**[math]** In 12-EDO there are `2^11 = 2048` possible scales containing the root. Any of them is a
valid scale object. Names exist for only a few.

**[math]** Useful scale operations (all mod N):

| Operation | Definition |
|---|---|
| transpose by k | add k to every element |
| rotate (mode) | re-root on another member, then subtract it from all members |
| invert | negate every element |
| complement | all pitch classes not in the set |

**[math]** *Modes* are rotations of one step pattern. Rotating `2 2 1 2 2 2 1` through its 7
starting points gives the 7 diatonic modes.

**[math]** *Generated scales.* Stack one interval (the *generator*) repeatedly, mod N. In 12-TET,
stacking the fifth (7 steps):

- 5 stacked fifths → pentatonic `{0, 2, 4, 7, 9}`
- 7 stacked fifths → diatonic `{0, 2, 4, 6, 7, 9, 11}` (the Lydian rotation)
- 12 stacked fifths → all 12 pitch classes

The diatonic and pentatonic scales come from the fifth itself. They have exactly two step sizes
(*well-formed* / *moment-of-symmetry* scales). Moving the root one generator along gives the
diatonic modes in order of brightness, each one lowering exactly one note:

| Fifths below root | Mode | Pitch classes |
|---|---|---|
| 0 | Lydian | 0 2 4 6 7 9 11 |
| 1 | Ionian | 0 2 4 5 7 9 11 |
| 2 | Mixolydian | 0 2 4 5 7 9 10 |
| 3 | Dorian | 0 2 3 5 7 9 10 |
| 4 | Aeolian | 0 2 3 5 7 8 10 |
| 5 | Phrygian | 0 1 3 5 7 8 10 |
| 6 | Locrian | 0 1 3 5 6 8 10 |

**[math]** *Symmetric scales* map onto themselves under some transposition, so they have fewer
distinct transpositions and modes (Messiaen's *modes of limited transposition*). Whole-tone
`{0,2,4,6,8,10}` has 2 transpositions; diminished/octatonic `{0,2,3,5,6,8,9,11}` has 3.

**[math]** *Maximal evenness* (Clough & Douthett 1991). Spreading k notes as evenly as possible
through N steps, `floor(i · N / k)` for `i = 0 … k−1`, produces many familiar structures from
just two numbers:

| k in 12 | Result |
|---|---|
| 3 | augmented triad |
| 4 | diminished seventh |
| 5 | pentatonic |
| 6 | whole-tone |
| 7 | diatonic (the Locrian rotation) |
| 8 | octatonic |

When k divides N the result is perfectly even, so it is symmetric and ambiguous (see §9).

**[convention]** The Greek mode names, "harmonic minor", "melodic minor" and so on are labels.
Harmonic and melodic minor are *alterations* of the diatonic scale, not generated scales. They are
as valid as any other set but are not derived from a single generator. Any set can be given any
name.

## 6. Chords

**[math]** A *chord* is a set of pitch classes sounded together, measured from its own root.
It is the same kind of object as a scale. The only difference is how it is used.

**[math]** *Stacking.* Build a chord from a scale by taking every *k*-th scale member from a
starting degree. With a 7-note diatonic scale:

- stride 2 → *tertian* chords (stacked thirds): 3 members = triad, 4 = seventh chord, 5–7 =
  extensions (9, 11, 13)
- stride 3 → *quartal* chords (stacked fourths)

The stride is a scale-degree count. The resulting step intervals depend on the scale. Stride 2 in
the diatonic scale gives 3- or 4-step gaps; in a pentatonic scale it gives different ones.

**[math]** *Why exactly two kinds of third.* In the diatonic scale, every stride (2nd, 3rd, 4th …)
comes in exactly two sizes (*Myhill's property*; such scales are *well-formed*). Stride 2 gives
3 or 4 steps, so stacked triads can only be built from minor and major thirds. Chord quality
follows from the scale's structure; it doesn't need to be listed.

**[math]** Stacking every degree of a 7-note diatonic scale with stride 2 gives triads with these
step sets (relative to each chord root):

| Steps | Label [convention] |
|---|---|
| 0 4 7 | major |
| 0 3 7 | minor |
| 0 3 6 | diminished |
| 0 4 8 | augmented *(not in diatonic; appears in harmonic/melodic minor)* |

**[physics]** `0 4 7` approximates the ratios 4:5:6, which are adjacent harmonics. `0 3 7`
approximates 10:12:15. These are measurable relationships. They do not mean one chord is "more
natural" than the other.

**[math]** *Inversions and voicings.* An inversion chooses which chord member is the lowest
sounding note. A *voicing* places each member in a specific octave (actual steps, not mod N).
Same pitch-class set, different arrangement.

**[math]** *Identification is ambiguous.* The same set can be read from different roots:
`{0, 3, 7, 9}` is a minor sixth chord on 0 *or* a half-diminished seventh on 9. Identifying a
chord means comparing the set against known patterns at every possible root. Choosing between
matches depends on context (bass note, function), which is a **[convention]**.

**[convention]** Chord names and symbols (`m7`, `ø7`, `sus4`, `add9`) are a lookup table from
step sets to strings. "Functional harmony" (tonic, dominant, cadences) is style, not physics.

## 7. Instruments

**[math]** An instrument maps *physical positions* to *pitches*. The theory above doesn't depend on
the instrument; the instrument only decides where each pitch can be played.

**[math]** *Keyboard.* One key per step, in a line: `pitch(key) = key`. A standard piano has 88
keys (A0–C8).

**[math]** *Fretted strings.* Each string has an open pitch, and each fret adds one step:
`pitch(string, fret) = open(string) + fret`. A string *tuning* is just the open pitches, so it can
be stored relative to the lowest string:

| Instrument | Gaps between strings (steps) |
|---|---|
| Guitar, standard | 5 5 5 4 5 |
| Bass, 4-string standard | 5 5 5 |
| Guitar, all-fourths | 5 5 5 5 5 |
| Guitar, DADGAD | 7 5 5 2 5 |

**[physics]** A string's frequency is inversely proportional to its vibrating length, so the fret
`k` steps up sits `L · (1 − 1/ratio(k))` from the nut (`L` the scale length): half way for the
octave, whatever the temperament. Frets get closer together up the neck, so a hand's reach is a
length, not a fret count. The span of frets 1–4 on a 648 mm guitar (97 mm) covers 6 frets from
the 12th, and fewer frets on an 864 mm bass. Touching a string at `L/n` brings out harmonic *n*:
the 12th fret (1/2), ≈7th fret (1/3), 5th fret (1/4).

**[physics]** *Capo.* A capo clamps every string at one fret: a movable nut. Open strings then
sound `c` steps higher and vibrate over `L / ratio(c)`, so a capoed neck is just a shorter neck
tuned higher, and fret distances, reach and frequencies follow from the same formula. **[convention]**
Tab for a capo counts frets from the capo (the capo is fret 0); some tab counts from the nut
instead. The code counts from the capo. Partial capos, which clamp only some strings, are not
modelled.

**[math]** *Every voicing.* A voicing gives each string a fret holding a chord tone, or mutes it,
so that every chord tone sounds and every fretted note is within the hand's reach. The code
builds all of them. The ways voicings of one chord differ can all be read off the fret numbers:

| Variation | Read from |
|---|---|
| Inversion | Chord tone of the lowest *pitch* (not lowest string: re-entrant tunings differ) |
| Top note | Chord tone of the highest pitch, which is heard as the melody |
| Spacing and doubling | The chord tones from lowest to highest pitch: close, open, drop voicings |
| String set | Which strings sound |
| Position | Where the hand sits: the lowest fretted note, under the index finger |

Everything else is a filter or a cost over that full list, so nothing is missed by construction.

**[physics]** *The hand.* Left-hand difficulty has three biomechanical sources, in this order of
weight: moving the hand along the neck, a wide finger span, and playing far from the middle of
the neck (Heijink & Meulenbroek 2002). Asked for the easiest fingerings, six professional
guitarists avoided moving the hand in 29 of 31 cases and spanned four frets in 29. A hand has
four fretting fingers, placed in fret order. One finger can *barre* notes at one fret. Fingers
reach over the neck from the highest string's side, so a barre lies from its first note to that
edge, and every string under it must be fretted at that fret or higher: an open string would be
damped and a lower note couldn't sound. So an A chord barred across the D, G and B strings loses
its open high E, and players either mute it or use three fingers. A muted string past the
barre's last note is fine, since it isn't played. Fingers are placed index first in fret
order, so none sits behind a lower-numbered one, and two fingers *k* apart reach at most what one
finger per fret allows at the nut, the widest frets (34, 67 and 97 mm on a 648 mm neck). A barre
lies along its whole fret, so no other finger can share that fret. Fingers crossing over each
other's strings are not modelled yet.

**[convention]** *Thumb over the neck (option, not built).* Some players fret the lowest string or
two with the thumb, wrapped over the top of the neck, which frees a finger. It belongs to some
styles and hands, not all, so it would be a separate rule a player opts into: allow one extra
fretted note on the lowest strings, at or behind the index finger's fret.

**[physics]** *Spacing.* The same chord is rougher when it is close and low, because the critical
band is wider at low frequencies (§2). That is the reason behind the spacing rule, wide
intervals at the bottom and close ones at the top (Huron 2001). A model fitted to how Bach
voiced 370 chorales scores each voicing by roughness alongside voice-leading distance, melody
motion and parallels (Harrison & Pearce 2020).

**[convention]** *Open strings far below the hand.* An open string is undamped by a finger and
rings longer than a fretted note, so it stands out, and up the neck its pitch is "left behind"
the fretted notes. Some styles want exactly that: campanella fingerings let open strings ring
against high fretted notes, and the open string often becomes the bass of a high voicing. Others
keep open strings within a few frets of the hand. So it is an opt-in rule with a limit: open
strings only with fretted notes at or below fret `n` (5 to 7 is a common taste). A capo moves
where "open" is, so it brings open strings back near a high hand.

**[convention, derived]** *How inversions are used.* The bass and the top voice are the most
audible lines (Huron 2001), and common practice uses inversions to shape the bass line. Root
position is the most stable (Lerdahl & Krumhansl 2007 count an inversion as 2 units of surface
tension, a top note other than the root as 1). The unstable second inversion (6/4) is used where
the bass holds (pedal 6/4) or passes by step (passing 6/4), and a seventh in the bass (4/2) falls
a step to a first inversion. All of these follow from one rule, *move the bass as little as
possible*, and the tests derive them that way.

**[convention]** *Choosing voicings on guitar.* Guitar teaching learns triads in all three
inversions on each set of adjacent strings, and seventh chords in all four (drop-2 and drop-3
voicings), then plays a progression in one position, moving to the nearest inversion.
That is the same as choosing the voicing path with the least hand movement, string-by-string
motion and roughness. The code scores each change by those measures and finds the cheapest path
through the whole progression. How much each measure weighs is not yet known for guitar.
Harrison & Pearce fitted such weights to Bach by maximum likelihood, and the same could be done
from a corpus of guitar tablature.

## 8. Melody and harmony

**[math]** Melody is a sequence of pitches over time; harmony is pitches at the same time. Both
are just sets or sequences of steps relative to a root, so all the operations above apply to
both.

**[convention]** Rules about which notes to play over which chord ("avoid notes", "chord-scale
theory") are style guidance. They can be built as optional rule sets on top of the math, never
inside it.

**[physics, perception]** *Voice leading.* Chords in sequence are heard as several melodic
lines at once, and the ear follows a line when its notes stay close in pitch. Many part-writing
rules follow from a few perceptual principles (Huron 2001): keep common tones, move other voices
by step, and avoid moving two voices in parallel perfect fifths or octaves, because voices that
far in tune fuse and are heard as one. Contrary motion, the melody against the bass, keeps the
lines most distinct.

**[math]** *Parsimonious moves.* Two triads sharing two notes are joined by moving the third note
one step: the neo-Riemannian P, L and R (Cohn 1997). Em to C (B to C) then C to Am (G to A) is
two such moves. Tymoczko argues the link to voice leading is only approximate, so the code
measures movement directly rather than naming transformations.

**[convention]** *Melody on top.* On guitar, a chord melody puts the melody in each chord's top
note and moves the inner voices by step beneath it. Harmonising a melody is then a search: for
each note, the chords allowed there (one fixed chord, or any chord of the key) and their voicings
with that note on top, linked by the cheapest path. Modes have signature moves the search finds
on its own, e.g. Phrygian's flat second falling to the root (F to E in E Phrygian) when a melody
passes through it.

**[math]** *Extensions.* Stacking a seven-note scale in thirds from any degree gives 1 3 5 7 9 11
13, and the next third is the root again two octaves up: a 13th chord is the whole scale. Any
extended chord (add9, 7th, 9th, 11th, 13th) is the root and third, which give its quality, plus
some of the rest, so extensions need no chord list. Each note is named by its place in the
stack, flat or sharp against the major scale: Em in E Phrygian stacks 1 b3 5 b7 b9 11 b13, so the
mode's F is Em's flat 9. **[convention]** Guitar voicings usually drop the 5th first, since the
root, 3rd and 7th define the chord. Between two chords, extended chords let the next chord's
notes arrive one or two at a time instead of all at once.

## 9. Tension and resolution

"Tension" is not a single quantity. It combines parts with different sources, and the code keeps
them separate.

| Component | Tag | Measured from |
|---|---|---|
| Roughness | **[physics]** | Partials of the actual voicing (Plomp & Levelt; Hutchinson & Knopoff) |
| Harmonicity | **[physics]** | Partials of the pitch classes (McDermott; Harrison & Pearce) |
| Inversion, top note other than the root | **[convention]** (learned) | A voicing and its root (Lerdahl & Krumhansl) |
| Voice-leading distance | **[math]** | Two pitch sets (Tymoczko) |
| Notes outside the current scale | **[math]** | A chord and a scale |
| Expectation, which note feels like home | **[convention]** (learned) | Listening experience (Krumhansl; Huron) |

**[math]** *Voice leading.* Pair each note of one chord with a note of the next, every note
taking part, and add up how far each moves. The *voice-leading distance* is the smallest
possible total.

**[math]** Small distance alone is not resolution. Into C major `{0,4,7}`, vi7 `{9,0,4,7}` moves
only 2 steps, and V7 `{7,11,2,5}` moves 4. Release needs a dissonance first that small motion
then removes. V7 → I, measured from the target root:

| Voice | Moves to | Steps |
|---|---|---|
| 7 | 7 | 0 (shared) |
| 11 | 0 | +1 (leading tone) |
| 2 | 0 | −2 |
| 5 | 4 | −1 (the seventh falls) |

`11` and `5` form a *tritone*: 6 steps, half the octave, the 12-TET step with no single simple
ratio (§3). Both its notes sit one step from a note of the target and move in opposite
directions.

**[math]** *Consequences, all derived rather than listed:*

- *Secondary dominants (tonicization).* Treat any chord root X as a temporary home. Its dominant
  is the four-note stacked chord on degree 5 of the major scale built on X. It adds exactly one
  note outside the key: X − 1, a leading tone into X.
- *Tritone substitution.* Transposing a dominant by N/2 keeps its tritone, because the tritone
  maps onto itself under that transposition.
- *Borrowed chords (modal mixture).* Chords stacked from a different rotation on the same root,
  e.g. Aeolian chords used in Ionian.
- *Neo-Riemannian moves.* Between major and minor triads, the moves P (`{0,4,7}→{0,3,7}`), L
  (`→{4,7,11}`) and R (`→{9,0,4}`) are the triad changes of distance 1, 1 and 2. Cohn showed
  this smoothness comes from the maths of 12 equal steps, not from acoustics.

**[physics, contested]** *Root motion by a fifth.* The dominant's root is the 3rd harmonic of the
target's root, so one theory (Rameau; later Terhardt and Parncutt's *virtual pitch*) says the
ear hears the target as the dominant's implied fundamental. Evidence is mixed and the theory
explains minor chords poorly, so the code doesn't depend on it.

**[convention]** Which chord sounds like "home" (*centricity*) is learned. Tymoczko lists it among
five features of tonality, with small melodic steps, acoustic consonance, chords of similar
structure, and a limited pool of notes. Only centricity is not computable from the sets
themselves.

## 10. Rhythm

**[physics]** Rhythm is periodicity below about 20 Hz. A 3:2 polyrhythm and a perfect fifth (3:2)
are the same ratio. Speed the rhythm up past ~20 Hz and it becomes the interval. So the ratio
maths of §2 applies to time as well.

**[math]** The model: a *cycle* of N beats, divided into *groups* (an ordered partition of N), each
beat split into *subdivisions*. Every quantity is a whole number. The main operations are
partitioning, subdividing, and lining up cycles of different length (their LCM).

**[convention]** Indian classical music names these structures explicitly:

| Concept | Hindustani | Carnatic |
|---|---|---|
| rhythmic cycle | tāl | tāḷa |
| beat unit | mātrā | akṣara |
| group / section | vibhāg | aṅga |
| first beat of the cycle | sam | samam |
| beat subdivision | laya (density) | naḍai / gati |

Carnatic *jāti* names the number used for a group length or subdivision:

| Jāti | Count | Solkaṭṭu (spoken syllables) |
|---|---|---|
| tiśra | 3 | ta ki ṭa |
| catuśra | 4 | ta ka di mi |
| khaṇḍa | 5 | ta ka ta ki ṭa |
| miśra | 7 | ta ki ṭa ta ka di mi |
| saṅkīrṇa | 9 | ta ka di mi ta ka ta ki ṭa |

Examples: Hindustani *Tīntāl* = 16 mātrās as 4+4+4+4 and *Rūpak tāl* = 7 as 3+2+2; Carnatic
*Ādi tāḷa* = 8 akṣaras as 4+2+2. Names can mislead: Carnatic *Rūpaka tāḷa* is a different
cycle (2+4 in its common form).
The *tihāī* (a phrase played three times so that it lands on sam) is a structural device whose
length is pure arithmetic.

**[math]** *A rhythm is a set on a circle.* Where notes start in a cycle of N pulses is a subset
of the integers mod N, exactly as a scale is a subset of the 12 steps (Toussaint 2013). The gaps
between onsets are its step pattern; displacing it is transposition; two rhythms are the same
pattern started elsewhere when they are rotations of each other (the same *necklace*). The
Euclidean rhythms are the maximally even sets of §5 (Demaine et al. 2009): E(3,8) is the
tresillo `3 3 2`, E(5,8) the cinquillo, and E(7,12) the West African bembé bell, whose gaps
`2 2 1 2 2 2 1` are the major scale's steps. A set is maximally even exactly when every span
(the distance covering k onsets, for each k) comes in one size or two consecutive sizes
(Clough & Douthett 1991); how far a rhythm is from that is a measure of its unevenness.

**[math]** *A meter is groups inside groups.* The cycle splits into groups, each group splits
again, down to the pulse. Two rules do every split. Heard as a meter, a multiple of 3 is
compound: beats of 3, themselves grouped (9 = 3+3+3, 12 = 6+6 then 3s, 15 = 6+9 then five 3s);
anything else splits in two, the shorter half first, until the groups are 2s and 3s
(4 = 2+2, 7 = 3+4 then 3+2+2). Spoken, every group splits in two, so konnakol's nine is 4+5
(*ta ka di mi ta ka ta ki ṭa*), where Western 9/8 is 3+3+3: the same number heard two ways, so
the rule is a parameter, not a fact. A pulse's *metrical weight* is how many levels start a
group on it, which reproduces Longuet-Higgins & Lee's 4/4 weights (1984). Beats split
differently (a quintuplet among sixteenths) share a grid of the least common multiple of their
divisions, so every position stays an integer.

**[math]** *Syncopation* (Longuet-Higgins & Lee 1984): a note followed by a silence stronger
than itself, before the next note, adds the difference in weight. Rhythms on the meter's own
levels score 0.

**[math]** *Counting fills.* The ordered ways to fill n pulses with parts from a set P satisfy
`c(n) = Σ c(n − p)`. With parts 1 and 2 these are the Fibonacci numbers, known to Indian
prosodists (Pingala, Hemachandra) as the count of metres of short and long syllables; with 2
and 3, the Padovan numbers: 7 pulses have exactly three groupings, 2+2+3, 2+3+2, 3+2+2.

**[math]** *Cadences are linear equations.* Three statements of p pulses with two gaps of g fill
`3p + 2g`. For 16, the only solutions are (4, 2) and (2, 5). A tihai of tihais (*chakradār*)
fills `9p + 6g + 2G` (65 = 64 + 1 in Tīntāl: a phrase of 7 nine times, one pulse between the
tihais). Statements growing or shrinking by d (*yati*: srotovaha, gopuccha) fill
`k·a + d·k(k−1)/2`. One solver lists every whole-number answer. Traditions count the landing
two ways: the last note *on* sam (Jhaptaal: 21 = 2 × 10 + 1) or the phrase ending *before* sam
(16 over 16), so the code asks which. A trio of equal or evenly growing parts always spans a
multiple of 3, so in a cycle of 12 it can never start on sam and land 1 or 2 pulses later
(Krishnaswamy & Wells 2023).

**[math]** *A phrase is three layers.* Spoken rhythm has a pulse, the syllables that sound on it,
and the words the syllables form, whose first syllables are the accents: "ta-ka-di-mi ta-ki-ta"
is seven onsets and two accents. A held syllable (*karvai*) is a longer duration, a gap a
silent token; words group into larger groups (the three statements of a tihai). The same tokens
can be regrouped (*gati bhedam*: a stream of 4s heard in 3s), played faster or slower (*kalam*:
every length halved or doubled), reversed, have their parts reordered (the *palta* of a qa'ida,
Kippen & Bel), or their sounds swapped (khali). Onsets and accents are each an ordinary rhythm
set, so every measure here applies to either.

**[convention]** *A cycle kept by hand.* A tāla is kept by gestures: in Carnatic music a laghu is a
clap then a finger counted on each beat, a drutam a clap and a wave, an anudrutam a clap; in
Hindustani music each vibhāg starts with a clap (sam marked X, then numbers) or a wave (khālī,
0). The gesture is a label, not a strength: khālī starts a section, yet it is the "empty" one,
played without the bass (Tīntāl's third section, *dha tin tin ta*).

**[math]** *Guest over host.* A repeating pattern laid over a meter disagrees with it in two
ways (Krebs 1999). A *grouping dissonance* G a/b: groups of a against groups of b, where neither
divides the other, counted in their largest common unit (every 3rd beat over a 4/4 bar is G3/4;
a hemiola is G3/2). A *displacement dissonance* D a+k: the same groups, shifted k units (late)
or −k (early). A G meets the host again after lcm(a, b) units (G3/4 after 12 beats); a D never
does. When only the guest sounds, the listener hears it against the meter they expect: Krebs'
*subliminal* dissonance.

**[physics]** *A stroke is two heads.* Most hand drums are a low head and a high head (or one
head struck low and high), each left to ring or damped; tabla strokes sort into exactly these
classes: damped, resonant treble, resonant bass, resonant both (Rohit & Rao 2021). Size sets the
pitch and damping the decay, so a stroke is two numbers and its sound follows from them.

**[convention]** *The bass marks the cycle.* A tabla theka drops the bass in its khali section,
so the listener hears where the cycle is from timbre alone. The default voicing here follows it:
the bass on notes that start a group above the count, the open high head on a count or an
inner group's start (the 3 of a five felt 2+3), a damped high head on any other note. Only notes
sound: a stroke on every silent point would bury the rhythm under its grid.

**[math]** *Timelines.* An ensemble often keeps time by a bell or clave pattern rather than a
pulse. Toussaint (2002) scores six 16-pulse timelines by metric complexity, 17 minus the sum of
Lerdahl & Jackendoff's weights (the weights of §10's 4/4 in sixteenths): shiko 2, son 4, rumba 5,
gahu 5, soukous 6, bossa-nova 6. Shiko and bossa-nova are palindromes, son is one about pulse 3,
and bossa-nova is maximally even.

**[math]** *Interlocking parts.* In Balinese kotekan each of two parts fills the other's gaps,
so the second part is the complement of the first on the grid; a sparser answer puts one note in
each gap, where the halving rule splits it. A *cadence* is a tihai built from a rhythm's own
opening: its first p pulses three times, g apart, with 3p + 2g filling the cycle.

**[convention]** Spoken words: 1 *ta*, 2 *ta ka*, 3 *ta ki ta*, 4 *ta ka di mi*; a longer group
is spoken as its two halves by the spoken rule above, which gives the jāti words in the table.
Syllable spellings differ by school and are data.

**[convention]** *Syllables say one of three things.* Konnakol says the place in the group (*ta-ki-ta*
is a group of three, whatever the beat). Takadimi (Hoffman, Pelto & White 1996) and "1 e & a"
say the place in the beat (*di* is always the middle). Tabla bols and taiko's kuchi shōga say
the sound (*dha* both drums open, *na* the treble ringing, *ti* damped; Rohit & Rao 2021 class
the bols this way). So one phrase can be spoken in any of them, and they differ only in what
the syllable is chosen by.

**[math]** *Measures of hearing.* The nPVI (Patel & Daniele 2003) is how much each duration
differs from the next; English instrumental themes score higher than French ones, as the two
languages' speech does, so it measures how speech-like a rhythm is. People synchronise with
events down to about 100 ms apart (Repp 2006); a faster level is texture, not count. A meter
of uneven beats is heard as one when its beats are maximally even in the grid (London 2012;
Polak & London 2014): 3+2+2 and 3+3+2, not 4+1+2. Medium syncopation draws the most desire to
move (Witek et al. 2014), so syncopation is shown, never maximised.

## Glossary

| Term | Meaning here |
|---|---|
| **step** | Smallest unit of a temperament (a semitone in 12-TET) |
| **N** | Number of steps per period (12 in 12-TET) |
| **period** | Interval after which pitch classes repeat (usually the octave, 2:1) |
| **temperament** | System mapping steps to frequency ratios (12-TET, 31-EDO, just intonation …) |
| **pitch class** | A pitch mod N |
| **root** | The reference pitch class (0) that a set is measured from |
| **interval** | Difference between two pitches: in steps, ratio or cents |
| **scale** | Pitch-class set used as the source of melody and harmony |
| **mode** | A rotation of a scale |
| **chord** | Pitch-class set sounded together, measured from its own root |
| **voicing** | A chord with actual octave placement |
| **string tuning** | An instrument's open-string pitches, *not* a temperament |
| **voice leading** | Pairing the notes of one chord with the next; its distance is the total movement |
| **tonicization** | Treating a chord root as a temporary home to derive chords around it |
| **cycle** | A repeating rhythmic frame of N beats |
| **pulse** | The finest grid point of a cycle; rhythms are sets of pulses |
| **onset** | A pulse where a note starts |
| **meter** | A cycle as groups inside groups; it says which pulses are strong |
| **host / guest** | The meter, and a repeating pattern laid over it |

## References

- Clough, J. & Douthett, J. (1991). Maximally even sets. *Journal of Music Theory* 35.
- Cohn, R. (1997). Neo-Riemannian operations, parsimonious trichords, and their *Tonnetz*
  representations. *Journal of Music Theory* 41.
- Demaine, E. et al. (2009). The distance geometry of music. *Computational Geometry* 42(5).
- Harrison, P. & Pearce, M. (2020). Simultaneous consonance in music perception and
  composition. *Psychological Review* 127(2).
- Harrison, P. & Pearce, M. (2020). A computational cognitive model for the analysis and
  generation of voice leadings. *Music Perception* 37(3).
- Heijink, H. & Meulenbroek, R. (2002). On the complexity of classical guitar playing:
  functional adaptations to task constraints. *Journal of Motor Behavior* 34(4).
- Huron, D. (2001). Tone and voice: a derivation of the rules of voice-leading from perceptual
  principles. *Music Perception* 19(1).
- Hutchinson, W. & Knopoff, L. (1978). The acoustic component of Western consonance.
  *Interface* 7.
- Jacoby, N. et al. (2019). Universal and non-universal features of musical pitch perception
  revealed by singing. *Current Biology* 29.
- Krebs, H. (1999). *Fantasy Pieces: Metrical Dissonance in the Music of Robert Schumann*.
  Oxford University Press.
- Lerdahl, F. & Krumhansl, C. (2007). Modeling tonal tension. *Music Perception* 24(4).
- Longuet-Higgins, H. C. & Lee, C. (1984). The rhythmic interpretation of monophonic music.
  *Music Perception* 1(4).
- McDermott, J., Lehr, A. & Oxenham, A. (2010). Individual differences reveal the basis of
  consonance. *Current Biology* 20.
- McDermott, J. et al. (2016). Indifference to dissonance in native Amazonians reveals cultural
  variation in music perception. *Nature* 535.
- Parncutt, R. (1988). Revision of Terhardt's model of the root(s) of a musical chord.
  *Music Perception* 6.
- Plomp, R. & Levelt, W. (1965). Tonal consonance and critical bandwidth. *JASA* 38.
- Rohit, M. A. & Rao, P. (2021). Automatic stroke classification of tabla accompaniment in
  Hindustani vocal concert audio. arXiv:2104.09064.
- Sethares, W. (2005). *Tuning, Timbre, Spectrum, Scale*. Springer.
- Toussaint, G. (2002). A mathematical analysis of African, Brazilian, and Cuban clave rhythms.
  *Bridges* 2002.
- Toussaint, G. (2013). *The Geometry of Musical Rhythm*. CRC Press.
- Hoffman, R., Pelto, W. & White, J. (1996). Takadimi: a beat-oriented system of rhythm
  pedagogy. *Journal of Music Theory Pedagogy* 10.
- Kippen, J. & Bel, B. (1992). Bol Processor grammars. In *Understanding Music with AI*. AAAI
  Press.
- Krishnaswamy, A. & Wells, R. (2023). The mathematics of the Carnatic kōrvai.
- London, J. (2012). *Hearing in Time: Psychological Aspects of Musical Meter* (2nd ed.). Oxford
  University Press.
- Patel, A. & Daniele, J. (2003). An empirical comparison of rhythm in language and music.
  *Cognition* 87.
- Polak, R. & London, J. (2014). Timing and meter in Mande drumming from Mali. *Music Theory
  Online* 20(1).
- Repp, B. (2006). Rate limits of sensorimotor synchronization. *Advances in Cognitive
  Psychology* 2.
- Witek, M. et al. (2014). Syncopation, body-movement and pleasure in groove music. *PLoS ONE*
  9(4).
- Tymoczko, D. (2011). *A Geometry of Music*. Oxford University Press.
