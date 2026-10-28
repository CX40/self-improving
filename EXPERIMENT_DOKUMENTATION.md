# Experiment-Dokumentation: Lokale Erprobung von Google Harness² (Recursive Agent Harnessing)

**Datum:** 28. Oktober 2026  
**Arbeitsverzeichnis:** `D:\DEV\AI\self-improving`  
**Referenz-Framework:** [Harness²: Recursive Agent Harnessing for an Open World](https://harness2.github.io/) (`google-research/harness2`, arXiv:2610.14224)

---

## 1. Hintergrund & Zielsetzung (Für Außenstehende erklärt)

### Was ist ein „Harness“ bei KI-Agenten?
Wenn ein Sprachmodell (LLM wie Claude oder Gemini) als autonomer **Agent** arbeitet, besteht das Gesamtsystem aus zwei Teilen:
$$\text{Agent} = \text{Modell } (\mathcal{M}, \text{eingefroren}) + \text{Harness } (\mathcal{H}, \text{editierbar})$$

Das **Harness** („Geschirr“ / Laufzeit-Gerüst) ist alles, was das Modell umgibt und steuert. In **Harness²** von Google Cloud AI Research ist dieses Harness kein einzelner System-Prompt mehr, sondern ein **Dateibaum aus 8 klar abgegrenzten Komponenten (`c1` bis `c8`)**:

| Nr. | Komponente | Pfad im Harness | Rolle & Kosten zur Laufzeit |
|---|---|---|---|
| **C1** | **System Prompt** | `systemprompt.md` | Persona & Basis-Prozedur (*Always-On* – kostet bei jedem Aufruf Kontext) |
| **C2** | **Guardrails** | `guardrails.md` | Feste Sicherheits- und Prüfregeln (*Always-On*) |
| **C3** | **Memory** | `LongTermMEMORY.md` | Dauerhafte Domänen-Fakten (*Always-On*) |
| **C4** | **Tool Guidance** | `tool_descriptions/tool_guidance.md` | Hinweise zur Werkzeugnutzung (*Always-On*) |
| **C5** | **Subagents** | `sub_agents/<name>/AGENT.md` | Delegierte Spezial-Agenten mit eigenem Kontext & Modell-Stufe (*On-Demand*) |
| **C6** | **Skills** | `skills/<name>/SKILL.md` | Wiederverwendbare Workflows, die nur bei Bedarf geladen werden (*On-Demand*) |
| **C7** | **Scripts** | `scripts/<name>.py` | Deterministische Python-Helfer für exakte Berechnungen (*On-Demand*) |
| **C8** | **Plugins / Hooks** | `plugin/<name>.ts` | Middleware, die direkt in die Tool-Schleife eingreift (*In-Loop Enforcement*) |

### Was macht Harness² besonders? (Die Zwei-Ebenen-Rekursion)
Klassische Agenten nutzen ein statisches, von Menschen geschriebenes Harness. **Harness²** optimiert das Harness **während der Arbeit an echten Aufgaben** völlig autonom – und zwar **ohne Musterlösung (Ground Truth)** und ohne Bewertungs-Rubrik:

1. **Ebene 1: Task-Level Recursion (`Propose → Probe → Compose` innerhalb einer Aufgabe)**
   * **Reference ($H_0$):** Der Agent führt die Aufgabe zunächst mit dem unveränderten Basis-Harness $H_0$ aus.
   * **Propose ($H_{inv}$ & $H_{dom}$):** Ein Improver-Modell untersucht den Ausführungs-Trace (Trajectory) und die erzeugten Dateien. Es schlägt zwei Arten von Harness-Änderungen vor:
     * *Invariant ($H_{inv}$):* Allgemeine Prozess-, Verifikations- oder Skript-Verbesserungen.
     * *Domain-Specific ($H_{dom}$):* Fachspezifische Regeln und Workflows für diese Domäne.
   * **Probe:** Beide Kandidaten-Harnesses werden live auf derselben Aufgabe ausgeführt.
   * **Compose ($H'$):** Ein Composer vergleicht alle Ausführungen rein anhand des **Verhaltens-Kontrasts (Behavioral Contrast)** – also wo ein Skript Fehler aufgedeckt hat, wo eine Prüfung stattfand oder wo Kantenfälle sauberer behandelt wurden – und baut daraus das finale Harness $H'$.
2. **Ebene 2: Harnessing-Level Recursion (`Reflect → Library Update` über Aufgaben hinweg)**
   * Nach Abschluss einer Aufgabe analysiert ein **Experience Reflector** den gesamten Verbesserungsprozess: *Welche Änderung am Harness hat das Verhalten des Agenten tatsächlich kausal verbessert – und welche Änderung wurde vom Agenten einfach ignoriert?*
   * Nur durch Evidenz belegte Lektionen wandern als `EXPERIENCE.md` samt dem adoptierten Harness in eine persistente **Domänen-Bibliothek (`library/`)**, auf die der Improver bei der nächsten Aufgabe zugreift.

---

## 2. Unser Versuchsaufbau (Lokal unter Windows + Multi-Tier-Modell-Routing)

Das offizielle Google-Repository ist eigentlich für Linux und Google Cloud Vertex AI ausgelegt. Um Harness² lokal unter Windows (`D:\DEV\AI\self-improving`) und ressourcenschonend über ein bestehendes **Claude-Abo (`claude` CLI)** auszuführen, haben wir folgende Architektur aufgebaut:

### 2.1 Technische Anpassungen am Framework
1. **Windows-Portierung der Core-Engine:**
   * **Dateisperren (`harness2/core/schedule.py`):** Das Linux-spezifische `fcntl.flock` wurde um einen plattformübergreifenden Fallback ergänzt.
   * **Pfad-Normalisierung (`harness2/core/tree.py`):** Unter Windows erzeugte `Path.relative_to()` Backslashes (`scripts\calc_sla.py`), wodurch die Regex-Oberflächenprüfung (`scripts/[a-z0-9_]+\.py`) von Harness² editierte Dateien verwarf. Durch Einbau von `normalize_rel()` in `read_tree()` wurden alle 8 Komponenten unter Windows voll editierbar.
2. **Direkte Anbindung an das lokale Abo (`harness2/core/proposer.py`):**
   * Der Zwang zu Google Cloud Vertex AI (`CLAUDE_CODE_USE_VERTEX=1`) wurde entkoppelt, sodass Harness² direkt die lokale `claude`-CLI mit `--model` und `--effort` anspricht.

### 2.2 Herstellerübergreifende Multi-Modell-Orchestrierung (Google Gemini + Anthropic Claude Tiers)
Ein besonderes Merkmal dieses Experiments ist das **intelligente Zusammenspiel verschiedener KI-Modelle unterschiedlicher Hersteller und Qualitätsstufen (Multi-Vendor & Multi-Tier Orchestration)**. Statt alle Aufgaben monoton über ein einziges teures Modell abzuwickeln, arbeitet hier eine exakt abgestimmte Arbeitsteilung aus **Google Gemini** und der **Anthropic Claude-Familie**:

| Rolle im System | Eingesetztes Modell | Hersteller | Aufwand / Tier | Warum genau dieses Modell für diese Rolle? |
|---|---|---|---|---|
| **Architekt, Portierung & Meta-Steuerung** | **Gemini 4 Argon** (in Devin) | **Google** | Medium / High | Analyse des Quellcodes von `google-research/harness2`, Windows-Portierung (`fcntl`, Pfad-Normalisierung), Entwurf der Benchmark-Umgebung (`live_multi_tier_demo.py`) und Steuerung des Gesamtexperiments. |
| **Solver / Executor (Aufgaben-Ausführung)** | **Claude Haiku 5.5** | **Anthropic** | `effort: low` (Schnell & günstig) | Führt die operativen Rollouts (`base1`, `inv1`, `dom1`, `agg1`) aus. Da im Harness²-Loop pro Aufgabe mehrere Probe-Läufe stattfinden, spart ein kleines, schnelles Modell massiv Token-Kontingent und Zeit. |
| **Improver (Proposer & Composer)** | **Claude Sonnet** | **Anthropic** | `effort: medium` (Code & Struktur) | Analysiert die Ausführungs-Traces des Haiku-Solvers, deckt Schwachstellen im Harness auf und programmiert selbstständig neue Python-Skripte (`scripts/`), Skills (`skills/`) und Prompts (`systemprompt.md`). |
| **Selector & Experience Reflector** | **Claude Opus** | **Anthropic** | `effort: high` (Tiefes Reasoning) | Übernimmt die anspruchsvollste kognitive Aufgabe: Den kausalen Vergleich aller Kandidaten-Läufe ohne Musterlösung und die Extraktion belastbarer Lektionen für die `EXPERIENCE.md`-Bibliothek. |
| **On-Demand Subagent-Dispatching (`C5`)** | **Dynamisch (`haiku` / `sonnet` / `opus`)** | **Anthropic** | Variabel je nach Teilaufgabe | Über den eingebauten `dispatch_subagent.py`-Mechanismus kann der Solver Teilaufgaben an spezialisierte `sub_agents/<name>/AGENT.md` delegieren, die im YAML-Frontmatter ihre eigene Modellstufe (`model: haiku|sonnet|opus`) definieren. |

**Warum diese hersteller- und stufenübergreifende Zusammenarbeit so wirkungsvoll ist:**
1. **Cross-Vendor-Synergie (Google + Anthropic):** Während das Framework `Harness²` sowie der übergeordnete Coding-Agent (**Gemini 4 Argon**) von Google stammen und die Systemarchitektur orchestrieren, agieren innerhalb der Rekursionsschleife die Modelle von Anthropic (**Claude Haiku, Sonnet, Opus**) als spezialisierte Rollenspieler.
2. **Ökonomische Skalierung (Token-Effizienz):** Im Harness²-Verfahren werden viele Ausführungen (*Probes*) benötigt, aber nur wenige Reflexionsschritte. Durch den Einsatz von **Haiku** als schnellem „Arbeiter“, **Sonnet** als „Ingenieur“ (Harness-Editor) und **Opus** als „Oberstem Prüfer“ (Reflector) erreicht man die Urteilskraft des größten Modells bei einem Bruchteil der Token-Kosten.
3. **Gegenseitige Kontrolle (Checks & Balances):** Ein Modell, das seine eigenen Ausgaben prüft, neigt zu blinden Flecken. Hier hingegen schreibt **Sonnet** neue Harness-Komponenten (wie `calc_sla.py`), **Haiku** testet sie unter realen Bedingungen im Workspace, und **Opus** deckt anschließend unbestechlich auf, ob Haiku die von Sonnet gebauten Werkzeuge tatsächlich genutzt oder ignoriert hat.

### 2.3 Die Test-Domäne: „SLA & Billing Reconciliation“ (`sla-audit-1` & `sla-audit-2`)
Wir haben zwei aufeinanderfolgende Aufgaben aus derselben Domäne (`sla_reconciliation`) entworfen. In jeder Aufgabe muss der Agent für zwei Unternehmenskunden aus drei Quellen (`contracts.md`, `incidents.log`, `ledger_adjustments.csv`) die exakte SLA-Gutschrift für Juli 2026 berechnen und als `audit_result.json` ausgeben.

**Eingebaute Domänen-Fallen in den Rohdaten:**
1. **Zeitzonen-Shift an Monatsgrenzen:** Ein Ausfall am `2026-06-30T22:30:00Z` liegt in UTC im Juni, für einen Kunden mit Vertragszeitzone `Europe/Berlin (UTC+2)` aber bereits am `01. Juli 00:30 Uhr` (zählt also!). Umgekehrt fällt `2026-07-01T02:00:00Z` für `America/New_York (UTC-4)` noch in den Juni (zählt nicht!).
2. **Dubletten im Log:** Manche `incident_id`-Einträge tauchen doppelt auf (erst als `SUPERSEDED`-Schätzung, dann als `RESOLVED`).
3. **Status-Filter:** Nur `OUTAGE` zählt, nicht `MAINTENANCE` oder `DEGRADED`.
4. **Vorab-Gutschriften (`PRE_CREDIT`):** Bereits gewährte Kulanzgutschriften müssen bei `remaining_credit_due_usd` abgezogen werden, dürfen aber `net_final_invoice_usd` nicht doppelt mindern.

**Die Sabotage im Basis-Harness ($H_0$):**
Um zu testen, wie Harness² mit einem schlechten Start-Harness umgeht, enthielt unser Basis-Harness $H_0$:
* Einen `systemprompt.md`, der den Agenten anweist: *„You are a fast billing assistant. Run `python scripts/calc_sla.py` to generate `audit_result.json` quickly and finish.“*
* Ein **absichtlich fehlerhaftes Skript `scripts/calc_sla.py`**, das stur nach `start_utc.startswith("2026-07")` filtert (Zeitzonen ignoriert), keine Dubletten entfernt und `PRE_CREDIT` unterschlägt.

---

## 3. Chronologischer Ablauf & Ergebnisse des Live-Experiments

### Phase 1: Erste Aufgabe (`sla-audit-1`)

#### Schritt 1.1: Basis-Ausführung (`base1` mit $H_0$)
Der `haiku`-Solver startet im Arbeitsverzeichnis. Er listet die Dateien auf und liest `contracts.md`, `incidents.log` und `ledger_adjustments.csv`.
* **Überraschendes Verhalten des Solvers:** Weil die Eingabedateien sehr kompakt waren (nur 9 Log-Zeilen), ignoriert `haiku` die Anweisung in `systemprompt.md` (`python scripts/calc_sla.py` auszuführen), rechnet alle Zeitzonen-Verschiebungen und Abzüge selbst im Kopf durch und schreibt `audit_result.json` direkt per `Write`-Tool (Score: **100 %**).
* **Aber:** In seiner Abschlussnachricht ist sich der Solver unsicher, ob `PRE_CREDIT` auch von `net_final_invoice_usd` abgezogen werden müsste (*„If the invoice should also net out the pre-credit, ACME's figure would be $8,500“*).

#### Schritt 1.2: Propose & Probe (`inv1` und `dom1` durch `sonnet`)
Der Improver (`sonnet`) bekommt den Trace von `base1` sowie das Basis-Harness $H_0$ vorgelegt (ohne zu wissen, ob die Zahlen von `base1` laut Musterlösung stimmen!).
Er erkennt sofort die Gefahr im Basis-Harness (`decisions/inv1.md` & `decisions/dom1.md`):
> *„The base harness told the solver to run a naive script... The old script filtered on UTC strings that start with `2026-07`. It did not dedupe incident IDs... Run as written, it would have given wrong minutes for both customers.“*

Der Improver erzeugt zwei Kandidaten-Harnesses:
* **Invarianter Kandidat (`inv1`):**
  * Schreibt `scripts/calc_sla.py` komplett neu (67 Zeilen Python mit `zoneinfo`-Zeitzonenkonvertierung, Regex-Parser für Vertragstabellen, `RESOLVED`-Deduplizierung und `PRE_CREDIT`-Verrechnung).
  * Ersetzt `systemprompt.md` durch eine 4-Schritte-Prozedur (Dateien ganz lesen $\rightarrow$ `calc_sla.py` ausführen $\rightarrow$ Trace gegen Vertrag prüfen $\rightarrow$ `audit_result.json` nochmals öffnen).
* **Domänen-Kandidat (`dom1`):**
  * Formuliert in `systemprompt.md` ein explizites 7-Punkte-Regelwerk für SLA-Abrechnungen (inklusive der Klarstellung: *„do NOT subtract PRE_CREDIT again“*) und legt ebenfalls ein korrigiertes `scripts/calc_sla.py` als Cross-Check bei.

#### Schritt 1.3: Compose (`agg1` durch `sonnet`)
Der Composer führt die besten Teile aus `inv1` und `dom1` in das finale Harness `agg1` zusammen. Im anschließenden Lauf (`agg1`) verschwindet die Unsicherheit des Solvers bezüglich `PRE_CREDIT`, und die Laufzeit sinkt von 17,6 s auf **14,3 s**.

---

### Phase 2: Der Aha-Moment – Kausale Reflexion durch `opus` (`EXPERIENCE.md`)

Jetzt folgt der Schritt, der **Harness²** von gewöhnlichen Prompt-Optimierern unterscheidet. Der Reflector (`opus`) vergleicht das adoptierte Harness `agg1` mit dem Basis-Harness `base` und prüft anhand aller vier Ausführungs-Traces (`base1`, `inv1`, `dom1`, `agg1`), **welche Harness-Änderung tatsächlich gewirkt hat**.

In `library/k1/agg/sla_reconciliation/harnesses/sla-audit-1/EXPERIENCE.md` schreibt `opus` eine bestechend scharfe Analyse:

1. **Entlarvung des scheinbaren Skript-Erfolgs (`verdict: no observed effect`):**
   > *„In none of the four trajectories (`base1`, `inv1`, `dom1`, `agg1`) did the solver run any version of the script. That includes `base1`, whose prompt said only 'run the script and finish' and whose script would have given wrong minutes... The script was invoked 0 times in 4 runs and the output file was re-opened 0 times. All four wrote identical JSON by hand right after reading the inputs. The claim in `decisions/inv1.md` that the script 'reproduces base1's values' came from the proposer, not from any solver run.“*
2. **Abgeleitete übertragbare Lektion (`Transferable lesson`):**
   * **Cue (Auslöser):** Die Eingabedateien sind klein genug, dass der Solver sie in einem Blick lesen und selbst ausrechnen kann, während das Harness ihn nur über Prosa im System-Prompt dazu auffordert, ein Helfer-Skript aufzurufen.
   * **Lesson (Lektion für künftige Improver):** *„Bevor du Änderungen an `scripts/<helper>.py` oder prozedurale Schritte in `systemprompt.md` als Erfolg verbuchest, zähle in den Trajectories nach, wie oft das Skript tatsächlich vom Solver aufgerufen wurde. Wenn es 0-mal aufgerufen wurde, bewerte den Edit als wirkungslos (`inert / no observed effect`)... Wenn das Helfer-Skript wirklich erzwungen werden muss, nutze einen Durchsetzungs-Mechanismus in der Tool-Schleife (z. B. ein Plugin/Hook) statt nur die Prosa umzuformulieren.“*

**Warum ist dieses Ergebnis so wichtig?**
Ein naives Selbstverbesserungs-System hätte sich selbst auf die Schulter geklopft: *„Ich habe `calc_sla.py` repariert und das Endergebnis war 100 % richtig – also war mein Skript-Edit super!“*
Harness² hingegen erkennt durch den **Verhaltens-Kontrast**, dass Korrelation nicht Kausalität ist: Das Skript war zwar objektiv repariert, wurde aber vom Agenten zur Laufzeit gar nicht aufgerufen.

---

### Phase 3: Zweite Aufgabe (`sla-audit-2`) – Lernen über Aufgaben hinweg

Bei der zweiten Aufgabe (`sla-audit-2`, neue Kunden `INITECH_DE` und `UMBRELLA_US`, andere Tarifstufen und Ausfallzeiten) startet der Executor vereinbarungsgemäß wieder beim Basis-Harness $H_0$, aber der **Improver hat nun Zugriff auf die `library/` aus Aufgabe 1**.

Man sieht sofort, wie der Improver in `sla-audit-2` seine Strategie ändert (`runs/sla-bench-oc-agg1/sla-audit-2/harnesses/agg1/`):
1. **Radikale Verschlankung des Always-On-Kontexts (`systemprompt.md`):**
   Statt langer Prozeduren in `systemprompt.md` reduziert er die Datei auf nur noch **2 Sätze (358 Bytes)** mit einem expliziten Skill-Trigger:
   ```markdown
   You are a billing auditor reconciling SLA downtime credits. Contracts (tier tables, billing timezone), incident log and ledger are the controlling sources; never rely on a canned calculation without checking it against them.
   When reconciling SLA credits from contracts, incident logs and a ledger, load the `sla-reconcile` skill before computing anything.
   ```
2. **Löschen des Altlast-Skripts:**
   Das fehlerhafte `scripts/calc_sla.py` wird komplett aus dem Harness gelöscht (`deleted`).
3. **Kapselung als On-Demand-Skill (`C6`):**
   Der Improver legt eine saubere Skill-Komponente an:
   * `skills/sla-reconcile/SKILL.md` (mit YAML-Frontmatter und den 7 exakten Domänen-Regeln)
   * `skills/sla-reconcile/scripts/sla_check.py` (ein gekapseltes Prüfskript direkt innerhalb des Skills).

Und auch nach `sla-audit-2` bleibt der Reflector (`opus`) in `reflection/agg1/edits.md` unbestechlich: Da auch bei `sla-audit-2` die Eingabedatei nur 8 Zeilen hatte und `haiku` die Lösung erneut direkt im Kopf berechnen konnte, ohne den Skill zu laden, vermerkt der Reflector erneut `verdict: no observed effect` und verhindert so, dass die Bibliothek mit unbewiesenen Behauptungen verschmutzt wird.

---

## 4. Zusammenfassung der wichtigsten Erkenntnisse

1. **Intelligente Zusammenarbeit verschiedener Hersteller & Modell-Generationen:**
   Das Experiment zeigt eindrucksvoll, wie sich unterschiedliche Modelle optimal ergänzen: **Google Gemini 4 Argon** adaptiert und steuert das Google-Research-Framework unter Windows, während innerhalb der Harness²-Pipeline **Anthropic Claude Haiku** (schnelle Rollouts), **Claude Sonnet** (Code- & Harness-Engineering) und **Claude Opus** (strenge Kausal-Reflexion) wie ein eingespieltes Team aus Junior-Analyst, Tool-Entwickler und Senior-Auditor zusammenarbeiten.
2. **Vollständige 8-Komponenten-Evolution statt reinem Prompt-Tuning:**
   Wir konnten live beobachten, wie Harness² eigenständig Python-Skripte (`scripts/calc_sla.py`) analysiert, Bugs darin findet (UTC-Falle, fehlende Deduplizierung, fehlendes `PRE_CREDIT`), sie neu programmiert, den `systemprompt.md` umbaut und in Aufgabe 2 eigenständig eine modulare Skill-Struktur (`skills/sla-reconcile/SKILL.md` + `scripts/sla_check.py`) anlegt.
2. **Strenge Evidenz-Kontrolle ohne Ground-Truth (Anti-Halluzination bei Self-Improvement):**
   Die größte Stärke von Harness² zeigte sich im Zusammenspiel von `sonnet` (Improver) und `opus` (Reflector): Obwohl der Improver ein fachlich perfektes Python-Skript geschrieben hatte, prüfte der Reflector anhand der echten Tool-Aufrufe im Ausführungs-Log (`trajectory.md`), ob der Solver dieses Skript überhaupt benutzt hat. So unterscheidet Harness² sauber zwischen *„Der Code im Harness sieht gut aus“* und *„Die Änderung hat das Verhalten des Agenten nachweislich verbessert“*.
3. **Wann greift der Solver tatsächlich zu Skripten und Subagenten (`C5` / `C7`)?**
   Genau wie vom Reflector in `EXPERIENCE.md` diagnostiziert: Solange die Eingabedateien so winzig sind (8 Zeilen), dass sie komplett in den ersten `cat`-Aufruf passen, löst selbst ein kleines Modell (`haiku`) die Aufgabe direkt im Kopf und überspringt externe Hilfsskripte oder Subagenten. Sobald die Datenmenge jedoch die Kopfrechen-Kapazität übersteigt (z. B. hunderte Log-Zeilen) oder ein `plugin/`-Hook (`C8`) die Verifikation in der Tool-Schleife erzwingt, wird das vom Improver gebaute Skript (`sla_check.py`) vom optionalen Helfer zum entscheidenden Erfolgsfaktor.

---

## 5. Übersicht der erzeugten Dateien im Projekt

* `D:\DEV\AI\self-improving\live_multi_tier_demo.py` – Unser Multi-Tier-Runner & Benchmark-Adapter (`haiku` / `sonnet` / `opus`).
* `D:\DEV\AI\self-improving\runs\live_sla_demo\library\k1\agg\sla_reconciliation\harnesses\sla-audit-1\EXPERIENCE.md` – Der vollständige Kausal-Bericht des `opus`-Reflectors nach Aufgabe 1.
* `D:\DEV\AI\self-improving\runs\live_sla_demo\runs\sla-bench-oc-agg1\sla-audit-1\harnesses\agg1\scripts\calc_sla.py` – Das vom Improver in Aufgabe 1 autonom reparierte Python-Skript.
* `D:\DEV\AI\self-improving\runs\live_sla_demo\runs\sla-bench-oc-agg1\sla-audit-2\harnesses\agg1\skills\sla-reconcile\SKILL.md` – Der vom Improver in Aufgabe 2 autonom angelegte On-Demand-Skill inkl. `sla_check.py`.
