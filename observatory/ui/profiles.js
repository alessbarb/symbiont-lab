import { state } from "../state/store.js";
import { availableEvents } from "../state/selectors.js";

function makeProfileSection(title, value, description) { const section=document.createElement("section");section.className="profile-section";const h=document.createElement("h3");h.textContent=title;const strong=document.createElement("strong");strong.textContent=value;const p=document.createElement("p");p.textContent=description;section.append(h,strong,p);return section; }

function renderProfiles() {
  const summary=document.querySelector("#summary-content");summary.replaceChildren();
  summary.append(makeProfileSection("Lifecycle", document.querySelector("#organism-state").textContent, "Current phase of the continuous cognitive cycle."));
  const physiology=state.physiology;
  summary.append(makeProfileSection("Rest intent", physiology ? (physiology.restingRequested ? "Requested" : "Not requested") : "Not exposed", "Passive physiology observation; Observatory cannot request or cancel rest."));
  const attention=state.attention;
  summary.append(makeProfileSection("Attention distribution", attention ? `${Math.round(attention.concentration*100)}% concentrated` : "Not exposed", attention ? `Entropy ${Math.round(attention.entropy*100)}%; bounded observation only.` : "No allocation metrics were published."));
  summary.append(makeProfileSection("Acclimation", `${Math.round(state.details.acclimation*100)}%`, "How much recent context has been incorporated — not a health or risk score."));
  const budget=document.createElement("section");budget.className="profile-section";const bh=document.createElement("h3");bh.textContent="Resource budget";budget.append(bh);[["CPU","cpu"],["Memory","memory"],["Storage","storage"]].forEach(([label,key])=>{const row=document.createElement("div");row.className="budget-row";const name=document.createElement("span");name.textContent=label;const raw=state.details.resourceBudget[key];const meter=document.createElement("i");const value=document.createElement("b");if(raw===null||raw===undefined){meter.style.setProperty("--value","0%");meter.classList.add("unmeasured");value.textContent="Not measured";}else{meter.style.setProperty("--value",`${raw*100}%`);value.textContent=`${Math.round(raw*100)}%`;}row.append(name,meter,value);budget.append(row)});summary.append(budget,makeProfileSection("Narrative","What it is doing",state.details.narrative));
  const organism=document.querySelector("#organism-details");organism.replaceChildren();[["Memory",state.details.memory],["Open questions",state.details.openQuestions],["Investigations",state.details.investigations],["Regime changes",state.details.regimeChanges]].forEach(([title,items])=>{const section=document.createElement("section");section.className="profile-section";const h=document.createElement("h3");h.textContent=title;const list=document.createElement("ul");list.className="detail-list";(items.length?items:["Nothing currently exposed"]).forEach((text,index)=>{const li=document.createElement("li");const b=document.createElement("b");b.textContent=`${title.replace(/s$/,"")} ${index+1}`;const span=document.createElement("span");span.textContent=text;li.append(b,span);list.append(li)});section.append(h,list);organism.append(section)});
  const socialSection=document.createElement("section");socialSection.className="profile-section";const socialTitle=document.createElement("h3");socialTitle.textContent="Social evidence";const socialNote=document.createElement("p");socialNote.textContent="Bounded observations only; this evidence is not an objective, ranking or peer label.";socialSection.append(socialTitle,socialNote);const socialList=document.createElement("ul");socialList.className="detail-list";const relations=Array.isArray(state.socialRelations)?state.socialRelations:[];(relations.length?relations:[null]).forEach(relation=>{const li=document.createElement("li");const b=document.createElement("b");b.textContent=relation?`${relation.source} → ${relation.target}`:"No social evidence exposed";const span=document.createElement("span");if(relation){const freshness=relation.freshness==null?"n/a":`${Math.round(relation.freshness*100)}%`;span.textContent=`${relation.valence}; channel ${relation.channel||"default"}; ${relation.observations} observations; reciprocal ${relation.reciprocalObservations}; support ${relation.support}; harm ${relation.harm}; reliability ${relation.reliability==null?"n/a":Math.round(relation.reliability*100)+"%"}; freshness ${freshness}; conflicts ${relation.conflicts}; rejections ${relation.rejections||0}`;}else span.textContent="The snapshot did not expose bounded relations.";li.append(b,span);socialList.append(li)});socialSection.append(socialList);organism.append(socialSection);
  const resourceSection=document.createElement("section");resourceSection.className="profile-section";const resourceTitle=document.createElement("h3");resourceTitle.textContent="Resource evidence";const resourceNote=document.createElement("p");resourceNote.textContent="Opaque local availability observations; not a host label or objective.";resourceSection.append(resourceTitle,resourceNote);const resourceList=document.createElement("ul");resourceList.className="detail-list";const resources=Array.isArray(state.socialResourceEvidence)?state.socialResourceEvidence:[];(resources.length?resources:[null]).forEach(item=>{const li=document.createElement("li");const b=document.createElement("b");b.textContent=item?item.token:"No resource evidence exposed";const span=document.createElement("span");span.textContent=item?`${Math.round(item.availability*100)}% available; ${item.observations} observations; denied ${item.denied}; freshness ${item.freshness==null?"n/a":Math.round(item.freshness*100)+"%"}`:"The snapshot did not expose bounded resource evidence.";li.append(b,span);resourceList.append(li)});resourceSection.append(resourceList);organism.append(resourceSection);const degradation=state.degradation||{retainedItems:0,excretedUnits:0};organism.append(makeProfileSection("Retention lifecycle","Bounded degradation",`Retained items: ${degradation.retainedItems}; excreted units this tick: ${degradation.excretedUnits}`));
  const research=document.querySelector("#research-details");research.replaceChildren();const dl=document.createElement("dl");dl.className="research-grid";
  const researchEntries = [
    ["Schema", `v${state.schemaVersion}`],
    ["Source", state.source],
    ["Tick", state.realTick ?? state.tick],
    ["Sequence", state.sequence == null ? "not published" : state.sequence],
    ["Run", state.runId ? state.runId.slice(0, 8) : "not published"],
    ["Last received", state.lastSnapshotAt ? new Date(state.lastSnapshotAt).toLocaleTimeString() : "not received"],
    ["Projection", "bounded, browser-local"],
    ["Percepts", state.senses.length],
    ["Beliefs", state.beliefs.length],
    ["Events", availableEvents().length],
    ["Population", state.population.length],
    ["Relationships", state.relationships.length],
    ["Ticks remaining", state.details.resourceBudget.ticksRemaining],
  ];
  if (state.source !== "demo") {
    researchEntries.push(
      ["Cognition", state.schemaVersion === 1 ? "native sensory development" : "structural graph"],
      ["Structural graph", state.schemaVersion === 1 ? "not configured" : "active"],
      ["Discovered", state.sampling.discovered],
      ["Active", state.sampling.active],
      ["Probing", state.sampling.probing],
      ["Dormant", state.sampling.dormant],
      ["Unknown", state.sampling.unknown],
      ["Sampled this tick", state.sampling.sampledThisTick],
      ["Development details exported", state.sensoryDevelopment.length],
      ["Strongest relations exported", state.sensoryRelations.length],
      ["Events retained locally", state.liveEvents.length],
    );
  }
  researchEntries.forEach(([label,value])=>{const div=document.createElement("div");const dt=document.createElement("dt");dt.textContent=label;const dd=document.createElement("dd");dd.textContent=String(value);div.append(dt,dd);dl.append(div)});research.append(dl);
}

function renderAccessibleTable() { const table=document.querySelector("#accessible-table");table.replaceChildren();const head=document.createElement("tr");["Type","Name","State","Value"].forEach(text=>{const th=document.createElement("th");th.textContent=text;head.append(th)});table.append(head);const rows=[...state.senses.map(item=>["Percept",item.name,item.active?"Available":"Unavailable",`${Math.round(item.quality*100)}%`]),...state.beliefs.map(item=>["Belief",item.title,item.dissent?"Contested":"Revisable",item.certainty.toFixed(2)]),...(Array.isArray(state.socialRelations)?state.socialRelations:[]).map(item=>["Social evidence",`${item.source} → ${item.target}`,item.valence,`${item.observations} observations; freshness ${item.freshness==null?"n/a":Math.round(item.freshness*100)+"%"}`])];rows.slice(0,160).forEach(values=>{const tr=document.createElement("tr");values.forEach(value=>{const td=document.createElement("td");td.textContent=String(value);tr.append(td)});table.append(tr)}); }

export { makeProfileSection, renderProfiles, renderAccessibleTable };
