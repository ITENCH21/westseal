"""
Fill body_en for all knowledge base articles.
Run: python manage.py fill_en_bodies
"""
from django.core.management.base import BaseCommand
from apps.core.models import Article

EN_BODIES = {
    "gost-hydraulic-seals": """<h2>Why standards matter</h2>
<p>Government standards (GOST) and international norms (ISO, DIN) define groove geometry, dimensional tolerances, material requirements, and seal testing conditions. Compliance with standards ensures interchangeability of parts, predictable service life, and hydraulic system safety.</p>

<h2>Key Russian and international standards</h2>
<ul>
  <li><strong>GOST 14896-84</strong> — rubber hydraulic seals. Defines types (1, 2, 3), size range from Ø6 to Ø500 mm, tolerances and technical requirements.</li>
  <li><strong>GOST 9833-73</strong> — rubber O-rings (circular cross-section). Covers sizes, hardness tolerances (IRHD 60–80) and material requirements.</li>
  <li><strong>GOST 16514-87</strong> — rubber wipers. Defines types and size range for protecting rods from contamination.</li>
  <li><strong>ISO 6194</strong> — radial shaft seals for rotating shafts (counterpart to GOST 8752-79).</li>
  <li><strong>DIN 3760 / ISO 6194-1</strong> — widely used for imported equipment.</li>
</ul>

<h2>Parameters defined by standards</h2>
<table class="article-table">
  <thead><tr><th>Parameter</th><th>What the standard defines</th></tr></thead>
  <tbody>
    <tr><td>Profile geometry</td><td>Shape, working lips, contact zone angle</td></tr>
    <tr><td>Size range</td><td>Inner/outer diameter, cross-section height</td></tr>
    <tr><td>Tolerances</td><td>Diameter and height deviations (h8, H9, etc.)</td></tr>
    <tr><td>Rubber hardness</td><td>Shore A or IRHD: typically 70–90 units</td></tr>
    <tr><td>Working temperature</td><td>Range by material (NBR, FKM, etc.)</td></tr>
    <tr><td>Test pressure</td><td>Minimum sealing requirements</td></tr>
  </tbody>
</table>

<h2>Choosing the right standard</h2>
<p>For Russian-manufactured equipment — look for GOST markings. For European imports (Bosch Rexroth, Parker, Festo) — use ISO/DIN. When replacing a worn seal, first measure the part and identify the profile type, then find the corresponding standard using reference tables.</p>
<p>Important: GOST and ISO size ranges do not always match — especially for non-standard diameters. In such cases we manufacture the seal to sample or drawing.</p>

<h2>Practical tip</h2>
<p>When submitting a selection request, specify the standard if known — this reduces processing time from 48 to 4–8 hours. If the standard is unknown, send a photo of the worn seal next to a ruler and describe the operating conditions.</p>""",

    "materials-selection": """<h2>Why material matters so much</h2>
<p>Incorrect material selection is the #1 cause of premature seal failure. Even a geometrically perfect seal made from an incompatible material will break down under the working medium within days.</p>

<h2>Main materials and their characteristics</h2>

<h3>NBR (nitrile butadiene rubber)</h3>
<ul>
  <li>Temperature range: −30…+100°C (up to +120°C short-term)</li>
  <li>Resistant to: mineral oils, water, diesel fuel, greases</li>
  <li>Not suitable for: aromatic hydrocarbons, ketones, strong acids</li>
  <li>Applications: hydraulics, pneumatics, fuel systems</li>
  <li>Hardness: 60–90 Shore A</li>
</ul>

<h3>HNBR (hydrogenated nitrile)</h3>
<ul>
  <li>Temperature range: −30…+150°C</li>
  <li>Resistant to: oils + ozone + hot water + steam</li>
  <li>Better than NBR at high loads and ozone exposure</li>
  <li>Applications: automotive industry, mining equipment</li>
</ul>

<h3>FKM (Viton® — fluoroelastomer)</h3>
<ul>
  <li>Temperature range: −20…+200°C (special grades up to +250°C)</li>
  <li>Resistant to: aggressive chemicals, fuels, acids, aromatics</li>
  <li>Not suitable for: hot water, steam, certain ketones</li>
  <li>Applications: chemical industry, aviation, oil & gas</li>
  <li>Cost 3–5× higher than NBR — justified in demanding conditions</li>
</ul>

<h3>PTFE (polytetrafluoroethylene, Teflon)</h3>
<ul>
  <li>Temperature range: −50…+250°C</li>
  <li>Minimum friction coefficient (0.05–0.10)</li>
  <li>Chemically inert to virtually all media</li>
  <li>Applications: food, pharmaceutical, chemical industries</li>
  <li>Drawback: cold flow — requires anti-extrusion rings</li>
</ul>

<h3>PU (polyurethane)</h3>
<ul>
  <li>Temperature range: −35…+100°C</li>
  <li>High wear resistance — 5–10× better than rubber</li>
  <li>Works well at high pressure (up to 400 bar)</li>
  <li>Applications: heavy hydraulic cylinders, construction machinery</li>
  <li>Not suitable for: hot water, alkalis, steam</li>
</ul>

<h2>Media-based selection table</h2>
<table class="article-table">
  <thead><tr><th>Medium</th><th>Recommended material</th></tr></thead>
  <tbody>
    <tr><td>Hydraulic oil (ISO VG)</td><td>NBR, PU</td></tr>
    <tr><td>Synthetic fluids HFB/HFC</td><td>EPDM, FKM</td></tr>
    <tr><td>Water, emulsions</td><td>NBR, EPDM, PTFE</td></tr>
    <tr><td>Diesel fuel</td><td>NBR, FKM</td></tr>
    <tr><td>Aggressive chemicals</td><td>FKM, PTFE</td></tr>
    <tr><td>Steam (above 120°C)</td><td>EPDM, PTFE</td></tr>
    <tr><td>Compressed air</td><td>NBR, PU, PTFE</td></tr>
  </tbody>
</table>

<h2>Practical selection algorithm</h2>
<ol>
  <li>Identify the working medium (oil, water, chemical)</li>
  <li>Determine the temperature range (min/max)</li>
  <li>Check the working pressure</li>
  <li>Assess movement speed (static / dynamic)</li>
  <li>Cross-reference with standard compatibility tables</li>
</ol>
<p>When in doubt — consult our specialists. Wrong selection costs more than the consultation.</p>""",

    "hydraulic-vs-pneumatic": """<h2>The fundamental difference in media</h2>
<p>Hydraulics works with incompressible fluid at pressures from 10 to 500+ bar. Pneumatics uses compressed air at 4–16 bar. This fundamental difference defines all seal requirements.</p>

<h2>Hydraulic seals</h2>
<h3>Key requirements:</h3>
<ul>
  <li><strong>Pressure-tight sealing</strong> — the primary function. Even minimal leakage is unacceptable.</li>
  <li><strong>High-pressure resistance</strong> — the profile must withstand extrusion into the clearance gap.</li>
  <li><strong>Wear resistance</strong> — high contact surface loads.</li>
</ul>

<h3>Typical profiles:</h3>
<ul>
  <li><strong>U-seals (UHS, UN)</strong> — for pistons and rods, working in one pressure direction</li>
  <li><strong>Double-acting seals (DH, DHS)</strong> — for bi-directional pressure</li>
  <li><strong>Piston rings</strong> — composite, providing low friction at high pressure</li>
  <li><strong>Guide rings</strong> — reduce misalignment and lateral loads</li>
</ul>

<h3>Materials:</h3>
<p>PU (polyurethane) — standard for heavy hydraulics. NBR — for light/medium systems. FKM — for aggressive media or high temperatures.</p>

<h2>Pneumatic seals</h2>
<h3>Key requirements:</h3>
<ul>
  <li><strong>Minimum friction</strong> — air provides no lubrication; friction without lubricant destroys the seal.</li>
  <li><strong>Easy stroke</strong> — low breakaway force for accurate positioning.</li>
  <li><strong>Dry-run resistance</strong> — intermittent operation without a lubricating film.</li>
</ul>

<h3>Typical profiles:</h3>
<ul>
  <li><strong>T-rings (T-seal)</strong> — lower friction than O-rings</li>
  <li><strong>Lip seals</strong> — soft contact, low friction</li>
  <li><strong>PTFE seals</strong> — for zero-friction applications</li>
</ul>

<h3>Materials:</h3>
<p>Low-hardness NBR (60–65 Shore A) — standard. PTFE — for minimum friction. Polyurethane — not used in pneumatics (dry-run destroys the surface).</p>

<h2>Comparison table</h2>
<table class="article-table">
  <thead><tr><th>Parameter</th><th>Hydraulics</th><th>Pneumatics</th></tr></thead>
  <tbody>
    <tr><td>Pressure</td><td>10–500+ bar</td><td>4–16 bar</td></tr>
    <tr><td>Lubrication</td><td>Fluid</td><td>Air (or ×oil mist)</td></tr>
    <tr><td>Primary requirement</td><td>Sealing integrity</td><td>Low friction</td></tr>
    <tr><td>Rubber hardness</td><td>80–90 Shore A</td><td>60–70 Shore A</td></tr>
    <tr><td>Primary material</td><td>PU, NBR</td><td>NBR, PTFE</td></tr>
    <tr><td>Profile</td><td>U, DH, composite</td><td>T, lip seals</td></tr>
  </tbody>
</table>

<h2>Common substitution errors</h2>
<p>Installing a hydraulic seal in a pneumatic cylinder is not acceptable — it is not designed for dry-run and will wear rapidly. The reverse substitution is also incorrect: a pneumatic seal cannot withstand hydraulic pressures.</p>""",

    "measuring-seals": """<h2>Why accurate measurements are critical</h2>
<p>A measurement error of just 0.5 mm can lead to wrong selection: the seal either won't fit in the groove, or will have insufficient interference and start leaking. Correct measurement is the foundation of accurate selection.</p>

<h2>Required tools</h2>
<ul>
  <li><strong>Calipers</strong> with 0.05 mm accuracy (digital preferred)</li>
  <li><strong>Micrometer</strong> — for cross-sections under 3 mm</li>
  <li><strong>Profile templates</strong> — for identifying seal type</li>
  <li><strong>Ruler or tape measure</strong> — for verification</li>
</ul>

<h2>What and how to measure</h2>

<h3>O-ring (circular cross-section ring)</h3>
<ul>
  <li><strong>d1 — cross-section diameter</strong>: measure the thickness of the ring in its relaxed state. Standard values: 1.5 / 2.0 / 2.5 / 3.0 / 4.0 / 5.0 / 6.0 mm</li>
  <li><strong>d2 — inner diameter</strong>: measure the ring from the inside. For accurate measurement, place the ring on paper, trace it — then measure the tracing.</li>
  <li>Formula for outer diameter: d2 + 2×d1</li>
</ul>

<h3>Lip seals (U-seal, DH-seal)</h3>
<ul>
  <li><strong>D — outer diameter</strong>: measure along the outer edge</li>
  <li><strong>d — inner diameter</strong>: along the inner edge (working diameter)</li>
  <li><strong>H — profile height</strong>: from the bottom base to the top point</li>
  <li>For a deformed seal, measure at multiple points and take the average</li>
</ul>

<h3>Wiper seals</h3>
<ul>
  <li>Measured the same way as lip seals: D, d, H</li>
  <li>Additionally — wiper type: open (single lip) or closed (double lip)</li>
</ul>

<h2>Standard tolerance table</h2>
<table class="article-table">
  <thead><tr><th>Bore diameter</th><th>Groove tolerance</th><th>Rod tolerance</th></tr></thead>
  <tbody>
    <tr><td>up to 50 mm</td><td>+0.1 / −0</td><td>−0.03 / −0.06</td></tr>
    <tr><td>50–100 mm</td><td>+0.12 / −0</td><td>−0.04 / −0.08</td></tr>
    <tr><td>100–200 mm</td><td>+0.15 / −0</td><td>−0.05 / −0.10</td></tr>
    <tr><td>200–500 mm</td><td>+0.20 / −0</td><td>−0.06 / −0.12</td></tr>
  </tbody>
</table>

<h2>Tips for non-standard cases</h2>
<ul>
  <li>If the seal is torn — measure from fragments, accounting for deformation.</li>
  <li>For old Soviet-era seals — look up dimensions in GOST 14896 or GOST 9833.</li>
  <li>If measurement is impossible — measure the groove dimensions instead: this gives the exact fit size.</li>
  <li>Place the seal on paper, trace it, and send us a photo with a scale reference — this is sufficient for selecting simple profiles.</li>
</ul>""",

    "failure-causes": """<h2>Reading the "history" of a worn seal</h2>
<p>The appearance of a failed seal is a diagnostic tool. The failure mode reveals the cause precisely — and helps eliminate it before the next replacement.</p>

<h2>Cause 1: Abrasive wear</h2>
<p><strong>Signs:</strong> uniform wearing of the working lip, rough surface, fine scoring.</p>
<p><strong>Causes:</strong> contaminated working medium, metal particles, dirt. Most often — missing or worn wiper seal.</p>
<p><strong>Solution:</strong> improve system filtration (≤10 µm for precision systems), install a quality wiper, check guide ring clearances.</p>

<h2>Cause 2: Extrusion into the gap</h2>
<p><strong>Signs:</strong> characteristic "ridge" or "skirt" on the low-pressure side of the seal, lip rupture.</p>
<p><strong>Causes:</strong> pressure exceeds material and clearance limits; installation clearance too large; material too soft for working pressure.</p>
<p><strong>Solution:</strong> reduce installation clearance (add a guide ring), choose harder material (Shore A 90+), use PTFE anti-extrusion rings.</p>

<h2>Cause 3: Thermal degradation</h2>
<p><strong>Signs:</strong> hardening, cracking, loss of elasticity, characteristic burnt rubber smell.</p>
<p><strong>Causes:</strong> temperature exceeds material limit; insufficient system cooling; high rod speed without lubrication.</p>
<p><strong>Solution:</strong> switch to wider temperature range material (HNBR, FKM), improve cooling, check speed and lubrication.</p>

<h2>Cause 4: Chemical incompatibility</h2>
<p><strong>Signs:</strong> swelling, delamination, blistering, loss of mechanical strength.</p>
<p><strong>Causes:</strong> wrong material for the working medium; change in fluid composition without updating seals.</p>
<p><strong>Solution:</strong> perform compatibility analysis, replace with chemically resistant material (FKM, PTFE).</p>

<h2>Cause 5: Installation damage</h2>
<p><strong>Signs:</strong> cuts, spiral scoring, puncture marks on the working surface.</p>
<p><strong>Causes:</strong> sharp edges during installation, assembly without lubricant or installation cone/sleeve, excessive bending during installation.</p>
<p><strong>Solution:</strong> 15–20° chamfers on all sharp edges, installation lubricant (compatible with medium), installation cone for splined rods.</p>

<h2>Cause 6: Dry running</h2>
<p><strong>Signs:</strong> striped wear pattern, surface adhesion, uneven abrasion.</p>
<p><strong>Causes:</strong> startup without working fluid, cavitation, insufficient lubrication in pneumatics.</p>
<p><strong>Solution:</strong> oil mist lubricator in pneumatic line, pre-lubrication during assembly, fluid level monitoring.</p>

<h2>Cause 7: Aging and ozone cracking</h2>
<p><strong>Signs:</strong> network of cracks across and along the seal, loss of elasticity without visible wear.</p>
<p><strong>Causes:</strong> exceeded storage life, ozone exposure (near electrical equipment), UV exposure.</p>
<p><strong>Solution:</strong> follow storage conditions, switch to ozone-resistant materials (EPDM, HNBR, FKM), comply with planned replacement schedules.</p>

<h2>Diagnostic table</h2>
<table class="article-table">
  <thead><tr><th>Visual sign</th><th>Most likely cause</th></tr></thead>
  <tbody>
    <tr><td>Ridge on edge</td><td>Extrusion (high pressure / large clearance)</td></tr>
    <tr><td>Spiral cut</td><td>Installation damage</td></tr>
    <tr><td>Uniform lip wear</td><td>Abrasive / contaminated medium</td></tr>
    <tr><td>Swelling, softness</td><td>Chemical incompatibility</td></tr>
    <tr><td>Surface cracking</td><td>Thermal degradation or aging</td></tr>
    <tr><td>Striped wear</td><td>Dry running</td></tr>
  </tbody>
</table>""",

    "storage-rules": """<h2>Why storage affects service life</h2>
<p>Rubber and polyurethane seals are living materials — they age even on the shelf. Improper storage destroys up to 50% of rated service life before installation. GOST 7338 and ISO 2230 establish strict requirements for storage conditions.</p>

<h2>Temperature and humidity</h2>
<ul>
  <li><strong>Optimal temperature:</strong> +5…+25°C</li>
  <li><strong>Maximum:</strong> +40°C (short-term)</li>
  <li><strong>Minimum:</strong> no lower than −10°C (rubber becomes brittle at low temperatures)</li>
  <li><strong>Relative humidity:</strong> 45–75%</li>
  <li>Avoid rooms near boiler rooms, heaters, open flame</li>
</ul>

<h2>Protection from ozone and UV</h2>
<p>Ozone is rubber's primary enemy. A concentration of just 0.01 parts per million triggers a chain reaction of cracking. Ozone sources: electric motors, transformers, welding equipment, fluorescent lamps.</p>
<ul>
  <li>Do not store near electrical equipment</li>
  <li>No direct sunlight (UV degrades anti-ozonants)</li>
  <li>Dark closed cabinets or boxes</li>
</ul>

<h2>Mechanical requirements</h2>
<ul>
  <li><strong>Do not deform profiles:</strong> do not fold seals or compress them under other parts. Deformation over 15% creates residual stresses.</li>
  <li><strong>Do not hang:</strong> O-rings should be stored flat or in coils with diameter no less than 150 mm.</li>
  <li><strong>Do not clamp:</strong> with wire or metal clamps — this causes cuts.</li>
</ul>

<h2>Packaging</h2>
<ul>
  <li>Original polyethylene packaging is the best solution. Do not open until use.</li>
  <li>For bulk storage — tight polyethylene bags with labeling.</li>
  <li>Do not use paper without a polyethylene barrier (paper absorbs moisture).</li>
  <li>Metal boxes with lids are suitable, but not in direct metal contact without a liner.</li>
</ul>

<h2>Shelf life by material</h2>
<table class="article-table">
  <thead><tr><th>Material</th><th>Recommended life</th><th>Maximum life</th></tr></thead>
  <tbody>
    <tr><td>NBR</td><td>2 years</td><td>5 years</td></tr>
    <tr><td>HNBR</td><td>3 years</td><td>7 years</td></tr>
    <tr><td>FKM (Viton)</td><td>5 years</td><td>15 years</td></tr>
    <tr><td>EPDM</td><td>3 years</td><td>7 years</td></tr>
    <tr><td>PTFE</td><td>10 years</td><td>Unlimited</td></tr>
    <tr><td>PU (polyurethane)</td><td>1 year</td><td>3 years</td></tr>
    <tr><td>Silicone</td><td>3 years</td><td>10 years</td></tr>
  </tbody>
</table>

<h2>What to do with seals after long storage</h2>
<ol>
  <li>Visual inspection — cracks, hardness, deformation?</li>
  <li>Check elasticity — the seal should recover its shape after 30% compression</li>
  <li>When in doubt — test under simulated conditions before installing on critical equipment</li>
</ol>""",

    "request-checklist": """<h2>Two selection scenarios</h2>
<p>Response time depends on the completeness of information provided:</p>
<ul>
  <li><strong>Complete information (checklist fulfilled):</strong> 4–8 hours</li>
  <li><strong>Partial information:</strong> 1–3 business days + follow-up questions</li>
  <li><strong>Only a photo of the worn seal:</strong> 2–5 business days</li>
</ul>

<h2>Required parameters</h2>

<h3>1. Unit type</h3>
<p>What does the component seal? Examples: hydraulic cylinder, pneumatic cylinder, pump, valve, rotary actuator, gearbox. This determines the motion type (reciprocating / rotary / static).</p>

<h3>2. Dimensions</h3>
<ul>
  <li>Rod or piston diameter (mm)</li>
  <li>Cylinder (bore) diameter</li>
  <li>Groove depth and width (if available)</li>
  <li>If no groove — dimensions of the sealing gap</li>
</ul>

<h3>3. Working pressure</h3>
<ul>
  <li>Nominal pressure (bar / MPa)</li>
  <li>Maximum (peak) pressure</li>
  <li>Single-acting or double-acting?</li>
</ul>

<h3>4. Movement speed</h3>
<p>Maximum rod or piston speed (m/s). Critical for material and profile selection. For rotary motion — rpm.</p>

<h3>5. Working temperature</h3>
<ul>
  <li>Minimum working temperature (°C)</li>
  <li>Maximum working temperature (°C)</li>
  <li>Storage / cold-start temperature</li>
</ul>

<h3>6. Working medium</h3>
<p>Exact name or type of fluid/gas: hydraulic oil VMGZ, ISO VG 46, AMG-10, water, emulsion, air, natural gas, acid, solvent, etc.</p>

<h2>Recommended parameters</h2>

<h3>7. Equipment manufacturer and model</h3>
<p>If known — this immediately provides access to the parts catalog and allows finding the original part number.</p>

<h3>8. Original part number or standard</h3>
<p>For example: SKF 20×40×7 HMS5 RG, Parker PDE-4, GOST 14896-84 Type 2. Enables selecting an exact analog.</p>

<h3>9. Reason for replacement</h3>
<p>Leakage, failure, scheduled maintenance? If failure — describe or send a photo of the worn seal. This helps eliminate the cause, not just the symptom.</p>

<h2>Additions that speed up selection</h2>
<ul>
  <li>📷 Photo of the seal next to a ruler</li>
  <li>📷 Photo of the groove (assembly)</li>
  <li>📄 Drawing or sketch with dimensions</li>
  <li>📄 Equipment manual (technical specifications page)</li>
</ul>

<h2>Request template</h2>
<p>Copy and fill in:</p>
<pre>Unit type: _____
Rod/piston diameter: _____ mm
Cylinder diameter: _____ mm
Groove depth: _____ mm / Width: _____ mm
Nominal pressure: _____ bar | peak: _____ bar
Speed: _____ m/s
Temperature: from _____ to _____°C
Medium: _____
Motion type: reciprocating / rotary / static
Equipment: _____
Additional info: _____</pre>""",

    "seal-kits": """<h2>What is a seal kit</h2>
<p>A seal kit (repair kit) — a complete set of all sealing elements for a specific assembly or unit: rod seals, piston seals, wiper, guide rings, O-rings for flanges and plugs. Manufactured to the equipment manufacturer's documentation.</p>

<h2>Financial comparison</h2>
<table class="article-table">
  <thead><tr><th>Approach</th><th>Cost</th><th>Downtime</th><th>Error risk</th></tr></thead>
  <tbody>
    <tr><td>Single part replacement</td><td>Low upfront</td><td>Less on first repair</td><td>High</td></tr>
    <tr><td>Full seal kit</td><td>Higher upfront</td><td>One shutdown</td><td>Minimal</td></tr>
    <tr><td>Replace only what broke</td><td>Appears cheaper</td><td>Repeat shutdown in 2–4 weeks</td><td>High</td></tr>
  </tbody>
</table>

<h2>Why replace everything at once?</h2>
<p>If the system has run for 2000 hours and one seal has failed, the others have also logged 2000 hours. Their service life is also nearly exhausted. With individual replacement, the second repair follows within weeks — with all the costs of repeat downtime, fluid drain, disassembly and reassembly.</p>

<h2>When seal kits are especially cost-effective</h2>
<ul>
  <li><strong>Preventive maintenance (PM):</strong> use a seal kit at every scheduled service.</li>
  <li><strong>High cost of downtime:</strong> mining equipment, presses, cranes — don't let a single seal cost a production cycle.</li>
  <li><strong>Hard-to-access assemblies:</strong> if disassembly takes more than 4 hours, replace everything while it's open.</li>
  <li><strong>Contract maintenance of an equipment fleet:</strong> standardized kits for identical machines.</li>
  <li><strong>Remote site maintenance:</strong> no possibility of quick ordering — better to have kits in stock.</li>
</ul>

<h2>When you can manage without a kit</h2>
<ul>
  <li>New equipment, isolated failure, other seals in good condition</li>
  <li>Easily accessible assembly, disassembly takes 20–30 minutes</li>
  <li>Emergency repair without planned shutdown — complete during next maintenance</li>
</ul>

<h2>How to store kits in stock</h2>
<ul>
  <li>Store in original packaging, unopened</li>
  <li>Label: equipment name, serial number, date received</li>
  <li>Follow storage conditions (temperature, ozone, UV)</li>
  <li>Monitor shelf life — use PU kits within 1–2 years</li>
  <li>Maintain a registry: equipment → seal kit → quantity in stock</li>
</ul>

<h2>How to order a seal kit</h2>
<p>Ideally — by the equipment manufacturer's catalog number. If the number is unknown: specify the make and model of the unit, type and year of manufacture. We will select an analog by dimensions and conditions. Non-standard kits can be manufactured to specific requirements.</p>""",

    "import-analogs": """<h2>Why analogs are needed</h2>
<p>Import seals (Parker, SKF, Trelleborg, NOK, Freudenberg) often have long lead times or cost several times more than domestic equivalents with comparable quality. A correctly selected analog does not reduce system service life or reliability.</p>

<h2>What is a "correct analog"</h2>
<p>An analog is not just a part that looks similar. It is a product that:</p>
<ul>
  <li>Has identical fitment dimensions (±0.05 mm for precision fits)</li>
  <li>Is made from a compatible material with the same operating parameters</li>
  <li>Provides the same or better sealing performance under working conditions</li>
</ul>

<h2>Selection methodology</h2>

<h3>Step 1: Geometry</h3>
<p>Using the catalog number or measurements, we determine exact dimensions: D, d, H, and profile. We compare with DIN/ISO/GOST tables. In most cases, standardized dimensions match between manufacturers.</p>

<h3>Step 2: Material</h3>
<p>From the original marking we determine the material. Designation examples:</p>
<ul>
  <li>NBR (N, 70N, 90N) — nitrile</li>
  <li>FKM (V, Viton, F) — fluoroelastomer</li>
  <li>PU — polyurethane</li>
  <li>PTFE (P, T) — polytetrafluoroethylene</li>
  <li>Numbers 70, 80, 90 — Shore A hardness</li>
</ul>

<h3>Step 3: Operating conditions</h3>
<p>We verify the analog's parameters against working conditions: pressure, temperature, medium, speed. For European catalogs we use DIN/ISO data sheets; for American — ASTM data.</p>

<h3>Step 4: Regulatory confirmation</h3>
<p>For critical applications (food industry, medical, oil & gas) we verify the analog complies with certifications: FDA 21 CFR, WRAS, ATEX, TR CU 010/2011.</p>

<h2>Common analog requests</h2>
<table class="article-table">
  <thead><tr><th>Original</th><th>What we look for</th><th>Selection source</th></tr></thead>
  <tbody>
    <tr><td>Parker PDE / SKF LDS</td><td>DIN 3760 / ISO 6194 size</td><td>GOST 8752 equivalent</td></tr>
    <tr><td>Trelleborg Turcon</td><td>PTFE profile with anti-extrusion</td><td>Russian PTFE manufacturer</td></tr>
    <tr><td>NOK hydraulic seals</td><td>PU U-seal size</td><td>Per DIN/ISO type</td></tr>
    <tr><td>Freudenberg Simrit</td><td>O-ring NBR/FKM</td><td>Per GOST 9833 or ISO 3601</td></tr>
  </tbody>
</table>

<h2>When an analog cannot be found</h2>
<ul>
  <li>Unique patented profile without a standard equivalent</li>
  <li>Special material (proprietary alloys, composites with classified composition)</li>
  <li>Certification requirements that a domestic analog does not meet</li>
</ul>
<p>In such cases we manufacture the seal to the original's sample or drawing.</p>

<h2>Analog selection lead times</h2>
<ul>
  <li>By known manufacturer catalog number: 1–2 hours</li>
  <li>By measurements and condition description: 4–24 hours</li>
  <li>By non-standard profile sample: 1–3 business days</li>
</ul>""",

    "temperature-ranges": """<h2>Why temperature range matters</h2>
<p>Every elastomer has its glass transition temperature (T<sub>g</sub>) — below which the material becomes brittle and cracks. At high temperatures, thermal degradation begins: loss of strength, the seal "fuses" to the surface, and leakage increases.</p>

<h2>Reference table of temperature ranges</h2>
<table class="article-table">
  <thead><tr><th>Material</th><th>Min °C</th><th>Normal °C</th><th>Max °C</th><th>Short-term max</th></tr></thead>
  <tbody>
    <tr><td>NBR standard</td><td>−30</td><td>+80</td><td>+100</td><td>+120°C / 1 hr</td></tr>
    <tr><td>NBR low-temp (LT)</td><td>−50</td><td>+70</td><td>+100</td><td>—</td></tr>
    <tr><td>HNBR</td><td>−30</td><td>+120</td><td>+150</td><td>+160°C / 1 hr</td></tr>
    <tr><td>FKM (Viton A)</td><td>−20</td><td>+150</td><td>+200</td><td>+230°C / 1 hr</td></tr>
    <tr><td>FKM (Viton GF)</td><td>−40</td><td>+150</td><td>+200</td><td>+230°C / 1 hr</td></tr>
    <tr><td>EPDM</td><td>−40</td><td>+120</td><td>+150</td><td>+160°C / 1 hr</td></tr>
    <tr><td>PTFE pure</td><td>−55</td><td>+200</td><td>+250</td><td>+260°C / 30 min</td></tr>
    <tr><td>PTFE filled</td><td>−55</td><td>+200</td><td>+260</td><td>+280°C / 30 min</td></tr>
    <tr><td>PU (polyurethane)</td><td>−35</td><td>+80</td><td>+100</td><td>+110°C / 30 min</td></tr>
    <tr><td>Silicone (VMQ)</td><td>−60</td><td>+150</td><td>+200</td><td>+230°C / 1 hr</td></tr>
    <tr><td>Fluorosilicone (FVMQ)</td><td>−65</td><td>+175</td><td>+200</td><td>+220°C / 1 hr</td></tr>
    <tr><td>PEEK (thermoplastic)</td><td>−70</td><td>+250</td><td>+280</td><td>+310°C / 30 min</td></tr>
  </tbody>
</table>

<h2>How pressure affects temperature limits</h2>
<p>Under high pressure, the maximum permissible operating temperature decreases. Approximate correction for NBR and PU:</p>
<ul>
  <li>Up to 100 bar: nominal range</li>
  <li>100–250 bar: reduce maximum by 10–15°C</li>
  <li>Above 250 bar: reduce maximum by 20–25°C</li>
</ul>
<p>For FKM and PTFE the reduction is less significant — these materials retain their properties under combined pressure and temperature loading.</p>

<h2>Cold start: selecting for low temperatures</h2>
<p>At startup in freezing conditions, the seal must maintain elasticity. Critical situations:</p>
<ul>
  <li>Construction equipment in Siberia: −50°C → NBR-LT or FKM GF needed</li>
  <li>Aviation hydraulic systems: to −65°C → FVMQ silicone or PTFE</li>
  <li>Northern offshore platforms: −40°C with oil → HNBR or FKM GF</li>
</ul>

<h2>Selection recommendations</h2>
<ul>
  <li>Always build in a ±15–20°C safety margin from the actual working range</li>
  <li>Account for startup temperature (cold start), not just steady-state operating temperature</li>
  <li>During heating and cooling cycles, seals experience thermocyclic loading — this shortens service life. For frequent cycling, choose FKM or HNBR.</li>
</ul>""",

    "pressure-speed": """<h2>Two primary loading parameters</h2>
<p>Pressure creates load on the seal profile, pressing it against the surface. Speed determines friction intensity at the contact zone. Both parameters simultaneously affect heat generation and wear — they must be evaluated together.</p>

<h2>Pressure: what happens when limits are exceeded</h2>
<h3>Extrusion into the gap</h3>
<p>When pressure exceeds the material and installation clearance limit, the seal begins to "extrude" into the gap between the piston/rod and cylinder. Sign: characteristic ridge on the low-pressure lip.</p>

<h3>Maximum pressure by material (without anti-extrusion rings)</h3>
<table class="article-table">
  <thead><tr><th>Material</th><th>Max pressure (static)</th><th>Max pressure (dynamic)</th><th>Max clearance</th></tr></thead>
  <tbody>
    <tr><td>NBR 70 Shore A</td><td>100 bar</td><td>60 bar</td><td>0.2 mm</td></tr>
    <tr><td>NBR 90 Shore A</td><td>200 bar</td><td>150 bar</td><td>0.1 mm</td></tr>
    <tr><td>PU 92 Shore A</td><td>400 bar</td><td>300 bar</td><td>0.05 mm</td></tr>
    <tr><td>FKM 80 Shore A</td><td>150 bar</td><td>100 bar</td><td>0.15 mm</td></tr>
    <tr><td>PTFE + anti-extrusion</td><td>700+ bar</td><td>500 bar</td><td>0.05 mm</td></tr>
  </tbody>
</table>

<h3>How to increase the permissible pressure</h3>
<ul>
  <li>Add an anti-extrusion ring made of PTFE or nylon</li>
  <li>Reduce installation clearance (tighter tolerances)</li>
  <li>Switch to a harder material</li>
  <li>Use composite seals (ring + anti-extrusion ring)</li>
</ul>

<h2>Speed: what happens when limits are exceeded</h2>
<h3>Heat generation</h3>
<p>Friction of the seal against the surface generates heat proportional to speed and contact pressure. Exceeding permissible speed → local overheating → accelerated aging → loss of sealing integrity.</p>

<h3>Maximum speeds by material</h3>
<table class="article-table">
  <thead><tr><th>Material / profile</th><th>Max dynamic speed</th></tr></thead>
  <tbody>
    <tr><td>NBR U-seal</td><td>0.5 m/s</td></tr>
    <tr><td>PU U-seal</td><td>1.0 m/s</td></tr>
    <tr><td>PTFE seal</td><td>5.0 m/s</td></tr>
    <tr><td>Composite seals (PTFE + elastomer)</td><td>3.0 m/s</td></tr>
    <tr><td>NBR O-ring (dynamic)</td><td>0.3 m/s</td></tr>
    <tr><td>Shaft seal (radial)</td><td>6–20 m/s (per DIN)</td></tr>
  </tbody>
</table>

<h3>The pv parameter — pressure × velocity</h3>
<p>To evaluate the combined effect, use the <strong>pv</strong> factor (MPa × m/s). Limit values:</p>
<ul>
  <li>NBR: pv ≤ 0.05 MPa·m/s</li>
  <li>PU: pv ≤ 0.3 MPa·m/s</li>
  <li>PTFE: pv ≤ 1.0 MPa·m/s</li>
</ul>
<p>Example: if pressure is 10 MPa (100 bar) and speed is 0.1 m/s, then pv = 1.0 — only acceptable for PTFE seals.</p>

<h2>Practical recommendations</h2>
<ul>
  <li>For high-speed systems: choose PTFE or composite seals with low friction</li>
  <li>For high pressure with low speed: PU, hard NBR, or composite solutions</li>
  <li>For combined high pressure and high speed: consult specialists — individual calculation required</li>
</ul>""",

    "wipers-guide-rings": """<h2>Why a wiper-less seal is doomed</h2>
<p>The primary function of a seal is to prevent fluid from leaking outward. But what protects the seal itself from external contamination entering the cylinder during rod extension? That is exactly the role of the wiper seal — the first line of defense against contaminants entering the cylinder as the rod strokes.</p>

<h2>How a wiper works</h2>
<p>As the rod retracts (rod entering the cylinder), the wiper scrapes dust, sand, metal particles, and other contaminants from the rod surface. Without it, abrasive material works under the working seal and wears it out in tens of hours instead of thousands.</p>

<h2>Wiper seal types</h2>
<h3>Single-lip (A-type)</h3>
<ul>
  <li>One working lip directed outward</li>
  <li>Application: standard conditions, light contamination</li>
  <li>Installation: in a groove or press-fit</li>
</ul>

<h3>Double-lip (B-type)</h3>
<ul>
  <li>Two lips: outer lip scrapes dirt, inner lip retains the oil film</li>
  <li>Application: severe conditions, construction / mining equipment</li>
  <li>Service life 2–3× higher than single-lip</li>
</ul>

<h3>Metal-cased stamped wiper</h3>
<ul>
  <li>Steel casing + rubber lip</li>
  <li>Application: precise positioning, large outer diameters</li>
  <li>Press-fitted into the cylinder body</li>
</ul>

<h3>PTFE wiper</h3>
<ul>
  <li>Minimum friction, chemical inertness</li>
  <li>Application: high-speed rods, aggressive media</li>
</ul>

<h2>Guide rings</h2>
<p>Guide rings (guide strips) — do not seal, but carry lateral loads. They prevent metal-to-metal contact between the piston/rod and the cylinder.</p>

<h3>Why guide rings are necessary</h3>
<ul>
  <li><strong>Reduce misalignment</strong> — under lateral loads, the piston stays centered</li>
  <li><strong>Protect the seal</strong> — without guides, the seal absorbs part of lateral load and wears rapidly on one side</li>
  <li><strong>Reduce friction</strong> — nylon/PTFE friction coefficient is lower than metal-on-metal</li>
  <li><strong>Absorb shock loads</strong> — especially important in mobile hydraulics</li>
</ul>

<h3>Guide ring materials</h3>
<table class="article-table">
  <thead><tr><th>Material</th><th>Load</th><th>Speed</th><th>Notes</th></tr></thead>
  <tbody>
    <tr><td>PTFE+bronze composite</td><td>High</td><td>High</td><td>Low friction, heat dissipation</td></tr>
    <tr><td>Polyamide (PA66+MoS2)</td><td>Medium</td><td>Medium</td><td>Good price/performance</td></tr>
    <tr><td>Filled nylon</td><td>Medium</td><td>Medium</td><td>Standard solution</td></tr>
    <tr><td>PEEK</td><td>Very high</td><td>High</td><td>Temperature up to +250°C</td></tr>
    <tr><td>Phenol-epoxy (textolite)</td><td>High</td><td>Low</td><td>Hydraulic presses</td></tr>
  </tbody>
</table>

<h2>Typical mistake: assembly without guide rings</h2>
<p>In budget repairs, guide rings are often omitted — "it'll work anyway." The result: seals wear unevenly, the cylinder starts to misalign, service life is reduced by 3–5×. A guide ring costs little but saves the entire seal kit.</p>""",

    "o-ring-selection": """<h2>O-ring — the world's most common seal</h2>
<p>The O-ring (circular cross-section ring) is used in more than 70% of all sealing applications. Its simplicity is deceptive: getting just one parameter wrong can eliminate the entire service life of the assembly.</p>

<h2>Designation system</h2>
<p>Standard designation: <strong>d2 × d1</strong>, where d2 is the inner diameter and d1 is the cross-section diameter.</p>
<p>Example: O-ring 50×3 = inner diameter 50 mm, cross-section 3 mm.</p>

<h2>Size standards</h2>
<table class="article-table">
  <thead><tr><th>Standard</th><th>Region</th><th>Cross-section series</th></tr></thead>
  <tbody>
    <tr><td>GOST 9833-73</td><td>Russia/CIS</td><td>1.68 / 2.65 / 3.55 / 5.30 / 7.0 mm</td></tr>
    <tr><td>ISO 3601-1</td><td>International</td><td>1.5 / 2.0 / 2.5 / 3.0 / 4.0 / 5.0 / 6.0 mm</td></tr>
    <tr><td>AS 568 (SAE)</td><td>USA</td><td>Inch series (similar cross-sections)</td></tr>
    <tr><td>DIN 3771</td><td>Germany</td><td>Metric series, close to ISO</td></tr>
    <tr><td>JIS B 2401</td><td>Japan</td><td>Series P, G, V, S</td></tr>
  </tbody>
</table>

<h2>Selecting cross-section diameter (d1)</h2>
<p>Cross-section is selected based on pressure and application type:</p>
<ul>
  <li><strong>1.5–2.0 mm</strong>: low pressure up to 10 bar, electronics, precision mechanics</li>
  <li><strong>2.5–3.0 mm</strong>: standard hydraulics, pneumatics up to 40 bar</li>
  <li><strong>4.0–5.0 mm</strong>: high pressure, heavy hydraulics up to 200 bar</li>
  <li><strong>6.0–7.0 mm</strong>: very high pressure, large assemblies</li>
</ul>

<h2>Hardness: Shore A vs IRHD</h2>
<table class="article-table">
  <thead><tr><th>Hardness</th><th>Application</th><th>Pressure</th></tr></thead>
  <tbody>
    <tr><td>60 Shore A</td><td>Pneumatics, low pressure</td><td>up to 25 bar</td></tr>
    <tr><td>70 Shore A</td><td>Standard applications</td><td>up to 80 bar</td></tr>
    <tr><td>80 Shore A</td><td>Hydraulics, medium pressures</td><td>up to 160 bar</td></tr>
    <tr><td>90 Shore A</td><td>High pressure</td><td>up to 250 bar</td></tr>
  </tbody>
</table>
<p>Too soft under high pressure → extrusion into gap. Too hard at low pressure → insufficient interference, leakage.</p>

<h2>Squeeze: optimal values</h2>
<p>The O-ring must be compressed by 10–30% of the cross-section diameter. Standard values:</p>
<ul>
  <li>Static seal: 15–25% compression (ensures sealing without high friction)</li>
  <li>Dynamic seal: 10–20% compression (less friction and wear)</li>
</ul>

<h2>O-ring in dynamic applications: limitations</h2>
<p>The O-ring is primarily a static seal. In dynamic applications (reciprocating motion) it is acceptable only when:</p>
<ul>
  <li>Rod speed ≤ 0.3 m/s</li>
  <li>Pressure ≤ 50 bar (without anti-extrusion ring)</li>
  <li>Good surface lubrication</li>
  <li>Rod surface finish Ra 0.4–0.8 µm (not polished and not rough)</li>
</ul>
<p>For higher speeds or pressures — use special profiles (U-ring, X-ring, T-ring).</p>

<h2>Most common mistakes</h2>
<ul>
  <li>Installing a twisted ring (spiral twist) — occurs when mounting over splines, causes immediate leakage</li>
  <li>Insufficient lubrication during installation — causes a cut from the groove edge</li>
  <li>Groove too large or too small — disrupts the interference fit</li>
  <li>Incompatible material — swelling or dissolution of the ring</li>
</ul>""",

    "ptfe-composites": """<h2>What is PTFE</h2>
<p>Polytetrafluoroethylene (PTFE, Teflon) is a synthetic fluoropolymer discovered in 1938 by DuPont. A unique material: it combines a temperature range of −55…+250°C, chemical inertness to virtually all known media, and the lowest friction coefficient among solid materials (0.04–0.10).</p>

<h2>Key PTFE properties</h2>
<table class="article-table">
  <thead><tr><th>Property</th><th>Value</th></tr></thead>
  <tbody>
    <tr><td>Temperature range</td><td>−55…+260°C</td></tr>
    <tr><td>Friction coefficient (sliding)</td><td>0.04–0.10</td></tr>
    <tr><td>Density</td><td>2.14–2.20 g/cm³</td></tr>
    <tr><td>Hardness Shore D</td><td>50–65</td></tr>
    <tr><td>Chemical resistance</td><td>Nearly universal</td></tr>
    <tr><td>Electrical strength</td><td>Excellent dielectric</td></tr>
    <tr><td>Vapor permeability</td><td>Zero</td></tr>
  </tbody>
</table>

<h2>Main drawback: cold flow</h2>
<p>Pure PTFE is prone to plastic deformation (cold flow) under load — even at room temperature. It gradually "flows" out of the groove, losing interference and sealing integrity. This is why <strong>filled composites</strong>, not pure PTFE, are used in power seals.</p>

<h2>Fillers and their effects</h2>
<table class="article-table">
  <thead><tr><th>Filler</th><th>Content</th><th>Effect</th></tr></thead>
  <tbody>
    <tr><td>Glass fiber (GF)</td><td>15–25%</td><td>Stiffness, wear resistance, reduced cold flow</td></tr>
    <tr><td>Bronze (Br)</td><td>40–60%</td><td>Heat dissipation, high load, dimensional stability</td></tr>
    <tr><td>Graphite (C)</td><td>5–15%</td><td>Additional lubrication in dry media</td></tr>
    <tr><td>Molybdenum disulfide (MoS2)</td><td>5%</td><td>Friction reduction at high pressure</td></tr>
    <tr><td>Carbon fiber (CF)</td><td>10–20%</td><td>Maximum wear resistance</td></tr>
    <tr><td>Aluminum oxide (Al₂O₃)</td><td>10–15%</td><td>Hardness, abrasion resistance</td></tr>
  </tbody>
</table>

<h2>Types of PTFE seals</h2>
<h3>Scraper rings and band seals</h3>
<p>Used as piston seals paired with an O-ring energizer. Work at speeds up to 5 m/s and pressures up to 500 bar (with anti-extrusion rings).</p>

<h3>Composite (compression) seals</h3>
<p>PTFE ring + elastomeric energizer (O-ring). The energizer provides initial interference and compensates for PTFE ring wear. Widely used in hydraulics with high speeds.</p>

<h3>V-packing (V-rings)</h3>
<p>Stacks of V-shaped PTFE rings under adjustable compression. Used in pumps, gate valves, and control valves. Allows adjusting compression as wear occurs.</p>

<h2>Typical application areas</h2>
<ul>
  <li><strong>Food industry:</strong> neutral to products, compliant with FDA 21 CFR §177.1550</li>
  <li><strong>Pharmaceuticals:</strong> steam sterilizable, zero leaching</li>
  <li><strong>Chemical industry:</strong> acids, alkalis, solvents</li>
  <li><strong>Oil & gas:</strong> downhole tools, high pressure + temperature</li>
  <li><strong>Aviation:</strong> wide temperature range, low weight</li>
  <li><strong>High-speed hydraulics:</strong> machine tools, precision drives</li>
</ul>

<h2>When PTFE is not the best choice</h2>
<ul>
  <li>Low speeds with high pressure without an O-ring energizer: cold flow will cause leakage</li>
  <li>Impact loads: PTFE is brittle under dynamic impacts</li>
  <li>Very low pressure: insufficient contact pressure without an energizer</li>
</ul>""",

    "seal-grooves": """<h2>Why groove geometry is critical</h2>
<p>A seal performs exactly as well as the groove it operates in is designed. A groove design error ruins the service life of even an excellent seal. Statistics show approximately 30% of premature failures are caused by groove geometry errors alone.</p>

<h2>Key groove parameters</h2>

<h3>Groove depth (h)</h3>
<p>Determines the compression (interference) of the seal. Too shallow: insufficient interference → leakage. Too deep: the seal "sinks" into the groove and creates no contact pressure.</p>
<p>Recommended O-ring compression: 10–25% of cross-section diameter d1.</p>
<p>Groove depth formula: h = d1 − (compression × d1) = d1 × (0.75…0.90)</p>

<h3>Groove width (b)</h3>
<p>Must give the O-ring or profile seal room to expand when compressed. Volume fill factor for an O-ring: 80–85% of groove volume.</p>
<p>If width is insufficient — the seal won't fit or deforms. If too wide — the seal "floats" and provides no sealing.</p>

<h3>Surface roughness</h3>
<table class="article-table">
  <thead><tr><th>Surface</th><th>Static Ra</th><th>Dynamic Ra</th></tr></thead>
  <tbody>
    <tr><td>Groove bottom</td><td>0.8–1.6 µm</td><td>0.4–0.8 µm</td></tr>
    <tr><td>Groove side walls</td><td>1.6–3.2 µm</td><td>1.6 µm</td></tr>
    <tr><td>Rod (sliding surface)</td><td>0.4–0.8 µm</td><td>0.2–0.4 µm</td></tr>
    <tr><td>Cylinder bore</td><td>0.4–0.8 µm</td><td>0.2–0.4 µm</td></tr>
  </tbody>
</table>
<p>Too smooth (Ra &lt; 0.1 µm) — seal sticks ("stick-slip"). Too rough — abrasive wear on the seal contact surface.</p>

<h3>Edge radii and chamfers</h3>
<p>Sharp edges are the primary cause of installation damage. Requirements:</p>
<ul>
  <li>Groove edges: radius R 0.2–0.5 mm or 0.3×45° chamfer</li>
  <li>Installation chamfers on rod/piston: 15–20° from axis, length ≥ 3 mm</li>
  <li>O-ring bore edges in housings: R 0.2–0.3 mm</li>
</ul>

<h2>Common errors and their consequences</h2>
<table class="article-table">
  <thead><tr><th>Error</th><th>Consequence</th></tr></thead>
  <tbody>
    <tr><td>Groove too deep</td><td>Insufficient interference → leakage at low pressure</td></tr>
    <tr><td>Groove too shallow</td><td>Excessive interference → high friction, accelerated wear</td></tr>
    <tr><td>Sharp groove edges</td><td>Seal cut during installation → failure at first pressurization</td></tr>
    <tr><td>No installation chamfer on rod</td><td>Cut during installation over splines/threads</td></tr>
    <tr><td>Surface roughness Ra too high</td><td>Abrasive wear of seal contact surface</td></tr>
    <tr><td>Groove too narrow</td><td>Seal won't fit, deforms during installation</td></tr>
    <tr><td>Groove too wide</td><td>"Floating" seal, lateral surface extrusion</td></tr>
  </tbody>
</table>

<h2>Recommended groove tolerances (per ISO 3601-2)</h2>
<p>For standard O-rings under static sealing:</p>
<ul>
  <li>Outer groove diameter: H9 (for the enclosing part)</li>
  <li>Inner groove diameter: h9 (for the enclosed part)</li>
  <li>Groove width: +0 / +0.1 from nominal</li>
</ul>

<h2>Volume fill verification formula</h2>
<p>The groove volume fill factor kv must be 75–85%:</p>
<p><strong>kv = (π × d1² / 4) / (b × h) × 100%</strong></p>
<p>Where d1 is the ring cross-section, b is groove width, h is groove depth.</p>""",

    "lead-time": """<h2>Typical lead times by seal type</h2>
<table class="article-table">
  <thead><tr><th>Type</th><th>In-stock lead time</th><th>Made-to-order</th></tr></thead>
  <tbody>
    <tr><td>Standard O-ring (GOST 9833)</td><td>1–2 days</td><td>5–10 days</td></tr>
    <tr><td>Standard hydraulic seal</td><td>1–3 days</td><td>7–14 days</td></tr>
    <tr><td>Non-standard PU seal</td><td>—</td><td>5–10 business days</td></tr>
    <tr><td>Shaft seal (GOST 8752)</td><td>1–2 days</td><td>10–14 days</td></tr>
    <tr><td>Custom PTFE seal</td><td>—</td><td>10–15 business days</td></tr>
    <tr><td>Seal kit per documentation</td><td>—</td><td>14–21 days</td></tr>
    <tr><td>Non-standard FKM seal</td><td>—</td><td>15–25 days</td></tr>
    <tr><td>Manufactured to sample/drawing</td><td>—</td><td>7–20 business days</td></tr>
  </tbody>
</table>

<h2>Factors affecting lead time</h2>

<h3>1. Material availability</h3>
<p>Standard NBR compound is typically in stock at most manufacturers. Special grades of FKM, HNBR, and silicone for specific applications may require raw material ordering.</p>

<h3>2. Profile complexity</h3>
<ul>
  <li><strong>Standard profile (O-ring, U-seal):</strong> tooling already exists</li>
  <li><strong>Complex profile (VRDE, SPGW, composite):</strong> requires special tooling</li>
  <li><strong>Non-standard profile per drawing:</strong> requires developing and manufacturing a mold (3–5 days)</li>
</ul>

<h3>3. Batch size</h3>
<ul>
  <li>Standard quantities from 100 pcs. — minimum launch time</li>
  <li>Small batches (1–10 pcs.) — often more expensive and longer: lower priority with manufacturers</li>
  <li>Large batches (from 1,000 pcs.) — planned in advance, may require more time for materials</li>
</ul>

<h3>4. Size range</h3>
<p>Very small (&lt;5 mm) and very large (&gt;400 mm) diameters are rarely stocked. The mid-range 20–200 mm is best covered.</p>

<h3>5. Certification requirements</h3>
<p>If documentation is required (compliance certificate, test report, quality passport) — add 1–3 days to the standard lead time.</p>

<h2>How to speed up seal delivery</h2>
<h3>Urgent orders</h3>
<ul>
  <li>Clearly state "Urgent" and your required date — we prioritize such requests</li>
  <li>Readiness for express delivery (air, courier) — discuss at order placement</li>
</ul>

<h3>Stock inventory</h3>
<p>The best way to avoid downtime is to keep critical items in stock. Recommendations:</p>
<ul>
  <li>Seal kits for key equipment: 2 kits per item</li>
  <li>O-rings of standard sizes: box stock of 50–100 pcs. for frequently used sizes</li>
  <li>Periodically review stock against shelf life</li>
</ul>

<h3>Size standardization</h3>
<p>When designing new equipment — use standard sizes from GOST or ISO. This reduces spare parts lead times in the future.</p>

<h2>Transparency on lead times</h2>
<p>We state real lead times at order confirmation and notify you of any changes in advance. For critical deadlines — let us know immediately, and we will find the optimal solution.</p>""",

    "engineering-support": """<h2>Why engineering support matters</h2>
<p>A seal is not just a "rubber ring." Incorrect seal selection can cause production shutdowns, accidents, or warranty claims. We don't simply ship catalog items — we help find the right solution for your specific task.</p>

<h2>Stage 1: Request intake and qualification</h2>
<p>Upon receiving a request, we assess its completeness. If sufficient data is provided — we proceed to selection. If not — we ask clarifying questions from the checklist (see the article "Checklist for seal selection").</p>
<p><strong>Goal:</strong> understand the real task, not just sell a part.</p>

<h2>Stage 2: Technical analysis</h2>
<p>Our specialists analyze the operating conditions:</p>
<ul>
  <li>Load type: static / reciprocating / rotary</li>
  <li>Speed regime: pv parameter, shock loads</li>
  <li>Thermal regime: working temperature, thermal cycles, cold start</li>
  <li>Medium: compatibility, aggressiveness, abrasive content</li>
  <li>Service life requirements: MTBF, maintainability</li>
</ul>

<h2>Stage 3: Solution selection</h2>
<p>Based on the analysis, we prepare 1–3 solution options with justification:</p>
<ul>
  <li><strong>Base option:</strong> optimal price/service life ratio</li>
  <li><strong>Extended option:</strong> increased service life (for demanding conditions)</li>
  <li><strong>Economy option:</strong> if task requirements allow</li>
</ul>

<h2>Stage 4: Specification agreement</h2>
<p>We prepare a specification stating:</p>
<ul>
  <li>Seal designation and standard</li>
  <li>Material with grade and hardness</li>
  <li>Exact dimensions and tolerances</li>
  <li>Operating conditions for which the solution was selected</li>
  <li>Installation recommendations</li>
</ul>
<p>The specification is agreed with the customer — this is a mutual understanding guarantee and the basis for any claims.</p>

<h2>Stage 5: Manufacturing and quality control</h2>
<p>Products are manufactured on certified equipment. Incoming inspection includes:</p>
<ul>
  <li>Geometric parameter measurement (10% of batch or 100% for critical items)</li>
  <li>Visual inspection for surface defects</li>
  <li>Hardness check (Shore A)</li>
  <li>For special products — media compatibility tests</li>
</ul>

<h2>Stage 6: Delivery and follow-up</h2>
<ul>
  <li>Packaging in compliance with storage conditions</li>
  <li>Quality passport / certificate of conformity (on request)</li>
  <li>Installation and storage guidelines included</li>
  <li>Follow-up 2–4 weeks after installation: is everything working correctly?</li>
</ul>

<h2>Complex cases: what we can solve</h2>
<ul>
  <li>Selection from a worn sample without a drawing</li>
  <li>Analogs for rare import profiles</li>
  <li>Seals for non-standard media (food production, aggressive chemicals)</li>
  <li>Complete seal kits per documentation or equipment specifications</li>
  <li>Emergency deliveries for production shutdowns</li>
</ul>

<h2>Contact an engineer</h2>
<p>Describe the task in any convenient way — via the request form, chat, or phone call. The more information you provide, the more accurately and quickly we will respond.</p>""",
}


class Command(BaseCommand):
    help = "Fill body_en for all knowledge base articles"

    def handle(self, *args, **options):
        updated = 0
        not_found = []
        for slug, body_en in EN_BODIES.items():
            try:
                article = Article.objects.get(slug=slug)
                article.body_en = body_en.strip()
                article.save(update_fields=["body_en"])
                updated += 1
                self.stdout.write(f"  ✓ {slug}")
            except Article.DoesNotExist:
                not_found.append(slug)
                self.stdout.write(self.style.WARNING(f"  ✗ NOT FOUND: {slug}"))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone: {updated} articles updated, {len(not_found)} not found"
        ))
        if not_found:
            self.stdout.write(f"Not found slugs: {not_found}")
