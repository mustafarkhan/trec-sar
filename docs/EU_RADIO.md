# European radio rules and the two-link mission

A rescue robot sold or operated in Europe cannot pick its own transmit power. This page states which limits
TREC-SAR's radio models assume, what a second, long-range narrowband link changes, and what it does not.

It is an engineering summary, not legal advice. National frequency tables can add conditions; check the national
regulator (Traficom in Finland) and the current standards before building hardware.

## The limits used

| Link | Band | Limit | Rule | In TREC-SAR |
|---|---|---|---|---|
| Video and control | 2400–2483.5 MHz wideband data | 100 mW (20 dBm) e.i.r.p., 10 dBm/MHz for non-hopping equipment | ETSI EN 300 328 | The default `LinkModel`: 20 dBm e.i.r.p., 4 dBi receive antenna, −90 dBm sensitivity, 10 dB fade margin |
| Telemetry and report, high power | 869.4–869.65 MHz (band h1.7) | 500 mW e.r.p., duty cycle ≤ 10 % (or listen-before-talk with frequency agility) | ERC Recommendation 70-03 Annex 1, ETSI EN 300 220 | Profile `eu868_500mw` |
| Telemetry and report, low power | 868.0–868.6 MHz (band h1.5) | 25 mW e.r.p., duty cycle ≤ 1 % (or listen-before-talk with frequency agility) | ERC Recommendation 70-03 Annex 1, ETSI EN 300 220 | Profile `eu868_25mw` |

Both 868 MHz profiles assume a LoRa modem at spreading factor 7 in 125 kHz: 5.47 kbit/s on air and −123 dBm
sensitivity (Semtech SX1276 class), a 2 dBi receive antenna and a 6 dB fade margin. Power limits given as e.r.p.
are converted to e.i.r.p. by adding 2.15 dB.

**The duty cycle is the point.** At 10 % the long-run data rate is 547 bit/s; at 1 % it is 55 bit/s.

| Payload | 500 mW, 10 % | 25 mW, 1 % |
|---|---|---|
| Position-only alert, 60 bytes | 0.9 s | 9 s |
| Report with a thermal thumbnail the operator can confirm, 4 kB | 59 s | 9 min 45 s |

## How the mission uses two links

```bash
trecsar compare --scenario forest_winter --seed 1002 --report-radio eu868_500mw
ros2 launch trecsar_bringup headless.launch.py report_radio:=eu868_500mw      # /link/report_margin_db
```

- **Supervision.** The robot counts as supervised where live video works *or* narrowband telemetry gets through.
  The link-loss failsafe, reactive relay drops and the planner's coverage test all use supervision. Relay nodes are
  assumed to repeat both bands.
- **Reporting.** On a detection the position goes out first on whichever link is up. For the confirmed report the
  robot compares the narrowband airtime of the thumbnail with the drive time to video coverage and takes the
  shorter: stay and transmit, or drive.
- **Success** still means the command post has something a human can confirm: live video or the thumbnail.

Live video is counted separately, so the cost of relying on telemetry is visible.

## What it changes — 200 held-out missions per policy on 8 terrains

| Forest, winter, 3 relays | Success | Median time to report | Relays used | Failsafe trips | Time without live video |
|---|---|---|---|---|---|
| Greedy + reactive relays, video link only | 74 % | 30.9 min | 2.4 | 0.7 | 1.3 min |
| TREC-SAR, video link only | 74 % | 30.4 min | 1.2 | 0.6 | 6.4 min |
| Greedy + reactive relays, with 868 MHz 500 mW | 73 % | 32.0 min | 0.7 | 0.0 | 17.4 min |
| TREC-SAR, with 868 MHz 500 mW | 71 % | 31.8 min | 0.2 | 0.5 | 17.6 min |

Full tables: [`results/summary.md`](../results/summary.md).

1. **In a 600 m forest a legal 868 MHz link supervises 87 % of the ground from the command post**, against 18 %
   for 2.4 GHz video (reference terrain, no relays). The failsafe problem disappears for every policy and most relays stay in the bay.
2. **It does not find people sooner.** Success and time to report are unchanged within the intervals.
3. **The operator pays in live video**: about 17 min per mission without it instead of 1–6 min.
4. **The duty cycle decides how reports travel.** At 10 %, 16 % of reports go out over 868 MHz from where the
   robot stands. At 1 % a thumbnail would take almost 10 min, so the robot always drives back to video coverage.
5. **Underground it changes nothing.** Rock blocks both bands, and a tunnel guides 868 MHz worse than 2.4 GHz
   (waveguide loss grows with wavelength squared). Planned relays and link-loss windows stay necessary there:
   TREC-SAR 91 % with 0.8 relays against 86–88 % with 2.6.

So the honest position for a European system is: fit the sub-GHz link, because it removes the supervision
problem above ground at almost no cost; keep link-aware planning for tunnels, large steel sites, and anywhere the
operator needs live video rather than telemetry.

## Assumptions behind these numbers

- Vegetation and structure loss at 868 MHz is 0.75 × the 2.4 GHz terrain value, from the f^0.284 frequency
  scaling of Weissberger's modified exponential decay model. A placeholder until measured.
- In the tunnel scenario 868 MHz loses 7.9 × more per metre than 2.4 GHz, the wavelength-squared scaling of
  waveguide loss (Emslie, Lagace & Strong, 1975). Real tunnels differ with cross-section and wall roughness.
- The data rate is bitrate × duty cycle. LoRa packet overhead, fragmentation of the thumbnail into 255-byte
  frames, acknowledgements and telemetry sharing the same airtime budget are not modelled; all of them make
  narrowband reports slower than stated.
- A heartbeat of about 30 bytes every 5 s uses roughly 1.3 % airtime at spreading factor 7: fine in the 10 % band,
  over the limit in the 1 % band, where telemetry would have to be slower.
- Treating telemetry as supervision is a design decision for the operator and the safety case, not a fact about
  radio. A system that needs live video to supervise autonomous motion should run without `--report-radio`.
- Listen-before-talk with adaptive frequency agility is the alternative to the duty-cycle limit and is not modelled.

## Sources

- ETSI EN 300 328, wideband transmission systems in the 2.4 GHz band.
- CEPT ERC Recommendation 70-03, Annex 1 (non-specific short range devices), bands h1.5 and h1.7; ETSI EN 300 220.
- Semtech SX1276/77/78/79 datasheet (LoRa sensitivity and bit rates).
- M. A. Weissberger, *An initial critical summary of models for predicting the attenuation of radio waves by
  trees*, ESD-TR-81-101, 1982.
- A. G. Emslie, R. L. Lagace, P. F. Strong, "Theory of the propagation of UHF radio waves in coal mine tunnels",
  *IEEE Transactions on Antennas and Propagation* 23(2), 1975.
