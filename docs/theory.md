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
pitch. Rhythm and pitch are the same thing at different speeds (see §9).

## 2. Intervals are ratios

**[math]** An *interval* is the ratio between two frequencies. Because hearing is logarithmic,
intervals are measured on a log scale. The standard unit is the *cent*:

```
cents(r) = 1200 · log2(r)
```

Intervals then *add* where ratios *multiply*: `cents(a·b) = cents(a) + cents(b)`.

**[physics]** The *octave* (2:1) is the simplest interval after unison. Every partial of the upper
note is also a partial of the lower one. Tones an octave apart are heard as "the same note,
higher" in most studied cultures (*octave equivalence*). This is why scales repeat every octave.

**[math]** The ratios between neighbouring harmonics give the simple intervals:

| Harmonics | Ratio | Cents | Common name |
|---|---|---|---|
| 2:1 | 2/1 | 1200.000 | octave |
| 3:2 | 3/2 | 701.955 | perfect fifth |
| 4:3 | 4/3 | 498.045 | perfect fourth |
| 5:4 | 5/4 | 386.314 | major third |
| 6:5 | 6/5 | 315.641 | minor third |
| 7:4 | 7/4 | 968.826 | harmonic seventh |

**[physics]** *Consonance* (how smooth an interval sounds) has a measurable physical part. When
partials of two tones are close but not equal, they *beat* and sound rough (Helmholtz; Plomp &
Levelt 1965). Simple ratios line up many partials exactly, so they produce little roughness.
That roughness depends on the timbre. With inharmonic timbres, different intervals sound smooth
(Sethares, *Tuning, Timbre, Spectrum, Scale*).

**[convention]** Ranking intervals by "consonance" beyond that physical part is learned and
cultural. The code can compute roughness or ratio simplicity, but it must not hard-code a ranking
of "good" and "bad" intervals.

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

**[physics]** Fret *k* in N-EDO sits at distance `L · (1 − 2^(−k/N))` from the nut, so frets get
closer together going up the neck. Touching a string at `L/n` brings out harmonic *n*: the
12th fret (1/2), ≈7th fret (1/3), 5th fret (1/4). A microtonal fretted instrument just uses a
different N.

## 8. Melody and harmony

**[math]** Melody is a sequence of pitches over time; harmony is pitches at the same time. Both
are just sets or sequences of steps relative to a root, so all the operations above apply to
both.

**[convention]** Rules about which notes to play over which chord ("avoid notes", "chord-scale
theory") are style guidance. They can be built as optional rule sets on top of the math, never
inside it.

## 9. Rhythm

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

Examples: *Tīntāl* = 16 mātrās as 4+4+4+4; *Rūpak* = 7 as 3+2+2; *Ādi tāḷa* = 8 as 4+2+2.
The *tihāī* (a phrase played three times so that it lands on sam) is a structural device whose
length is pure arithmetic.

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
| **cycle** | A repeating rhythmic frame of N beats |
