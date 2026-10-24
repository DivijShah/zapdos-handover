window.SITE = {
 "stats": {
  "open": 10,
  "in_progress": 5,
  "waiting_owner": 11,
  "done": 4,
  "superseded": 0,
  "questions": 11
 },
 "last_action": {
  "type": "send",
  "persona": "priya",
  "at": "2026-10-24T15:00:00-05:00",
  "path": "outbox/sent/20261024-1500-priya-reply-lisa-case-study.md"
 },
 "clock": "2026-10-24T15:00:00-05:00",
 "people": [
  {
   "id": "sam",
   "name": "Sam Rivera",
   "role": "Founder",
   "owed": [
    {
     "id": "9a98b2c1a2",
     "title": "Optix PO by Tue 27 Oct 17:00 (50% upfront)",
     "due": "Tue 27 Oct",
     "overdue": false,
     "status": "open",
     "sources": [
      "C09",
      "E10",
      "CAL07"
     ],
     "notes": [
      "Calendar event for the Optix PO deadline on 2026-10-27 at 17:00, attendee Sam."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "1486390443",
     "title": "Bayview pilot pass bar (signed)",
     "due": "",
     "overdue": false,
     "status": "open",
     "sources": [
      "C05",
      "S015",
      "L-ZAP-141"
     ],
     "notes": [
      "Linear ticket ZAP-141 is Todo, unassigned, no due date."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    }
   ],
   "waiting": [
    {
     "id": "36ddde2532",
     "text": "What customer price should Northwind (Maria) be quoted for the 12-door dock cameras? The pack only has supplier cost (\"Attached quote: 12 x OX-4K dome, $4,680 total [fictional]. 2-week lead time. Need a PO by Tue 27 Oct to hold stock. 50% upfront.\", E10), not a sell price. Brief is in the outbox.",
     "from": "sam",
     "re": "a9227252ec",
     "due": "Thu 22 Oct",
     "due_src": null
    },
    {
     "id": "a13162c7e1",
     "text": "Approve reimbursing Wei Lin? \"Wei Lin paid $640 out of pocket for the Harbor Point site trip. Needs Sam's approval to reimburse.\" (C10, ZAP-160). Nothing will be paid without your approval; test mode only.",
     "from": "sam",
     "re": "a2d9f52dc3",
     "due": "",
     "due_src": null
    },
    {
     "id": "e2c4270926",
     "text": "Rachel wants 2 customer references by Wed 28 Oct (C06). Only one pilot customer (Bayview) appears in the pack. Who is the second reference, and has each customer given permission?",
     "from": "sam",
     "re": "f3804a88c5",
     "due": "Wed 28 Oct",
     "due_src": null
    },
    {
     "id": "3dd5a834ca",
     "text": "What ballpark price range should Omar at Ridgeline get? He asked to get budget (E09). The pack has no Ridgeline price.",
     "from": "sam",
     "re": "908bc52ca9",
     "due": "",
     "due_src": null
    },
    {
     "id": "842f3bda13",
     "text": "Where should Jordan go on Monday morning? He asked (E06) and no office address or location exists anywhere in the pack. The reply draft in the outbox says you will confirm; nothing has been sent.",
     "from": "sam",
     "re": "46192cbd69",
     "due": "",
     "due_src": null
    }
   ],
   "handed": [],
   "done": [
    {
     "id": "75ec07a571",
     "title": "Reply to Maria's chase (Northwind)",
     "due": "",
     "overdue": false,
     "status": "done",
     "sources": [
      "E15"
     ],
     "notes": [
      "Maria chased Sam asking whether the project is still on."
     ],
     "flags": []
    },
    {
     "id": "46192cbd69:send",
     "title": "SENT: Re: Monday?",
     "due": "",
     "overdue": false,
     "status": "sent",
     "sources": [
      "E06",
      "C04"
     ],
     "notes": [
      "→ jordan.lee@mail.example  ·  outbox/sent/20261024-1500-sam-reply-jordan-monday.md"
     ],
     "flags": []
    },
    {
     "id": "75ec07a571:send",
     "title": "SENT: Re: Dock cameras",
     "due": "",
     "overdue": false,
     "status": "sent",
     "sources": [
      "E15",
      "E03",
      "C01",
      "L-ZAP-101"
     ],
     "notes": [
      "→ maria.gomez@northwind-cold.example  ·  outbox/sent/20261024-1500-sam-reply-maria-northwind.md"
     ],
     "flags": []
    }
   ],
   "superseded": [],
   "asked": 5
  },
  {
   "id": "weilin",
   "name": "Wei Lin Tan",
   "role": "Engineer",
   "owed": [
    {
     "id": "52a1cfd904",
     "title": "Onboard Jordan: accounts, laptop, first task, buddy",
     "due": "Sun 25 Oct",
     "overdue": false,
     "status": "open",
     "sources": [
      "C04",
      "S006",
      "E06",
      "L-ZAP-130"
     ],
     "notes": [
      "Ticket unassigned, status Todo, due 2026-10-25; Jordan starts Mon 26 Oct."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "3ec65c1e02",
     "title": "30s night-shift clip for Monday post",
     "due": "Mon 26 Oct",
     "overdue": false,
     "status": "open",
     "sources": [
      "C08",
      "S010",
      "L-ZAP-171"
     ],
     "notes": [
      "Ticket is unassigned, status Todo, due 2026-10-26."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "b3aad8dc79",
     "title": "Harbor Point: relocate cam 3 (rack in bay C)",
     "due": "Mon 02 Nov",
     "overdue": false,
     "status": "open",
     "sources": [
      "C02",
      "WA01",
      "L-ZAP-110"
     ],
     "notes": [
      "photo received (WA01); Raj proposes 2 m left onto column"
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "7173cc1d4d",
     "title": "Harbor Point install: 6 cams, paint shop",
     "due": "Tue 03 Nov",
     "overdue": false,
     "status": "open",
     "sources": [
      "C02",
      "S001",
      "E02",
      "C10",
      "CAL01"
     ],
     "notes": [
      "Install scheduled for Tue 3 Nov."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "1dabedf067",
     "title": "Bayview night glare false alerts (cams 2, 5)",
     "due": "",
     "overdue": false,
     "status": "open",
     "sources": [
      "C05",
      "E07",
      "S014",
      "WA04",
      "L-ZAP-140"
     ],
     "notes": [
      "Alerts improved on cam 2 but still bad on cam 5 at Bayview."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "92c7d9ee68",
     "title": "Bayview weekly Friday report",
     "due": "",
     "overdue": false,
     "status": "open",
     "sources": [
      "C05",
      "E07",
      "CAL05",
      "L-ZAP-142"
     ],
     "notes": [
      "Ticket in Backlog, unassigned, no due date."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "0cc2b9431a",
     "title": "Demo floor-by-floor progress tracking on Crestline call",
     "due": "",
     "overdue": false,
     "status": "open",
     "sources": [
      "WA03"
     ],
     "notes": [
      "Farah asks for a floor-by-floor progress tracking demo by the engineer on the call."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "84e5515f15",
     "title": "Document how deploy alerts are wired",
     "due": "",
     "overdue": false,
     "status": "in_progress",
     "sources": [
      "S007",
      "C10",
      "L-ZAP-161"
     ],
     "notes": [
      "Ticket in Backlog, unassigned; Alex on leave."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    }
   ],
   "waiting": [
    {
     "id": "665a4176e0",
     "text": "Does the quoted camera match your layout? Optix quote Q-1182: \"Attached quote: 12 x OX-4K dome, $4,680 total [fictional]. 2-week lead time. Need a PO by Tue 27 Oct to hold stock. 50% upfront.\" (E10). You have not seen it (C09). Sam needs to know before the PO (due Tue 27 Oct).",
     "from": "weilin",
     "re": "8cadc92446",
     "due": "",
     "due_src": null
    },
    {
     "id": "c0f37290f9",
     "text": "Can the Harbor Point install start at 13:30 instead of 14:00? Raj asked (WA02); forklifts move at 16:00. The reply draft in the outbox commits no time; nothing has been sent.",
     "from": "weilin",
     "re": "8a5a9fb60f",
     "due": "",
     "due_src": null
    },
    {
     "id": "17004d1e5c",
     "text": "Ken asks: \"Do you need a VLAN?\" (E04). The pack does not say. What should the reply tell him? The draft in the outbox confirms the IPs and says you will answer; nothing has been sent.",
     "from": "weilin",
     "re": "6a5790396f",
     "due": "",
     "due_src": null
    }
   ],
   "handed": [
    {
     "text": "Crestline call 2026-11-03 15:00-15:45 SGT (CAL02). Farah asked Dana by WhatsApp: \"Hi Dana, quick one: can the engineer show us how you track progress floor by floor on the call?\" (WA03). You were not copied on the one-pager email either (E05).",
     "cite": [
      "CAL02",
      "WA03",
      "E05"
     ],
     "from": "weilin"
    },
    {
     "text": "Heads-up: you are double-booked on 3 Nov. Harbor Point Yard install 2026-11-03 14:00-16:30 vs Crestline Data Centers call 2026-11-03 15:00-15:45 (SGT). Dana's AI drafted a reschedule note to Farah and asked Dana whether to send it. Raj's 13:30 start request (WA02) is still waiting for your answer.",
     "cite": [
      "C03",
      "E05",
      "CAL01",
      "CAL02",
      "WA02"
     ],
     "from": "dana"
    }
   ],
   "done": [
    {
     "id": "184d262a60",
     "title": "Northwind dock camera layout (doors 1-12)",
     "due": "Thu 22 Oct",
     "overdue": false,
     "status": "done",
     "sources": [
      "C01",
      "E01",
      "S003",
      "S004",
      "L-ZAP-101",
      "L-ZAP-103"
     ],
     "notes": [
      "Wei Lin finished layout v2 and put it in Drive."
     ],
     "flags": []
    },
    {
     "id": "16c9c02c48",
     "title": "Harbor Point camera IP range from Ken",
     "due": "Mon 02 Nov",
     "overdue": false,
     "status": "done",
     "sources": [
      "C02",
      "S001",
      "E02",
      "E04",
      "L-ZAP-111"
     ],
     "notes": [
      "IPs received (E04); VLAN question open"
     ],
     "flags": []
    },
    {
     "id": "8a5a9fb60f:send",
     "title": "SENT: Re: Tuesday start time",
     "due": "",
     "overdue": false,
     "status": "sent",
     "sources": [
      "WA02",
      "E02"
     ],
     "notes": [
      "→ Raj Kumar, Harbor Point (WhatsApp; no email address in pack)  ·  outbox/sent/20261024-1500-weilin-reply-raj-start-time.md"
     ],
     "flags": []
    },
    {
     "id": "6a5790396f:send",
     "title": "SENT: Re: IP range for Tuesday 3 Nov install",
     "due": "",
     "overdue": false,
     "status": "sent",
     "sources": [
      "E04",
      "E02"
     ],
     "notes": [
      "→ ken.ong@harborpoint.example  ·  outbox/sent/20261024-1500-weilin-reply-ken-ips-vlan.md"
     ],
     "flags": []
    }
   ],
   "superseded": [],
   "asked": 3
  },
  {
   "id": "dana",
   "name": "Dana Brooks",
   "role": "Sales caller",
   "owed": [
    {
     "id": "a3229fed02",
     "title": "Book Cedar call: Rachel with an engineer",
     "due": "",
     "overdue": false,
     "status": "open",
     "sources": [
      "C06",
      "E08"
     ],
     "notes": [
      "Rachel asks for a 20-minute call with an engineer; not yet booked."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "91ae534556",
     "title": "Send Crestline one-pager to Farah",
     "due": "",
     "overdue": false,
     "status": "in_progress",
     "sources": [
      "C03",
      "E05",
      "S016"
     ],
     "notes": [
      "Dana asks whether the Crestline one-pager was sent; no confirmation given."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "35efac7f1f",
     "title": "Book next call with Tom Reyes (Northwind)",
     "due": "",
     "overdue": false,
     "status": "in_progress",
     "sources": [
      "C01",
      "E01",
      "E03",
      "L-ZAP-104"
     ],
     "notes": [
      "Linear ticket ZAP-104 is unassigned and in Todo status."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    }
   ],
   "waiting": [
    {
     "id": "5bb664a8bb",
     "text": "Send the reschedule draft to Farah? Wei Lin is double-booked: Harbor Point Yard install 2026-11-03 14:00-16:30 vs Crestline Data Centers call 2026-11-03 15:00-15:45 (SGT). Draft is in the outbox; nothing has been sent.",
     "from": "dana",
     "re": "601a2158f7",
     "due": "",
     "due_src": null
    },
    {
     "id": "685fda0c60",
     "text": "Who from Zapdemo attends the Ridgeline site visit on Tuesday or Wednesday morning? Omar asked (E09). The pack does not say who goes; Wei Lin is the engineer.",
     "from": "dana",
     "re": "8b2f334ef4",
     "due": "",
     "due_src": null
    }
   ],
   "handed": [],
   "done": [
    {
     "id": "aec4099af8",
     "title": "Crestline engineer call (3 Nov 15:00 SGT)",
     "due": "Tue 03 Nov",
     "overdue": false,
     "status": "done",
     "sources": [
      "C03",
      "S002",
      "CAL02"
     ],
     "notes": [
      "Call with Dana and Wei Lin is on the calendar for 3 Nov 15:00-15:45 (+08:00)."
     ],
     "flags": []
    },
    {
     "id": "35efac7f1f:send",
     "title": "SENT: New times for our next call with Tom",
     "due": "",
     "overdue": false,
     "status": "sent",
     "sources": [
      "E03",
      "C01",
      "L-ZAP-104"
     ],
     "notes": [
      "→ maria.gomez@northwind-cold.example  ·  outbox/sent/20261024-1500-dana-tom-call-reask-maria.md"
     ],
     "flags": []
    }
   ],
   "superseded": [],
   "asked": 2
  },
  {
   "id": "priya",
   "name": "Priya Nair",
   "role": "Content",
   "owed": [
    {
     "id": "b3a8d80bb0",
     "title": "Crestline one-pager",
     "due": "Mon 02 Nov",
     "overdue": false,
     "status": "in_progress",
     "sources": [
      "C03",
      "L-ZAP-120"
     ],
     "notes": [
      "Ticket is unassigned, status Todo, due 2026-11-02; promised by Dana."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    },
    {
     "id": "da00b3a116",
     "title": "Northwind pallet-damage one-pager for Maria's VP",
     "due": "",
     "overdue": false,
     "status": "in_progress",
     "sources": [
      "C01",
      "C08",
      "S011",
      "L-ZAP-105"
     ],
     "notes": [
      "Linear ticket ZAP-105 in Backlog, unassigned, no due date."
     ],
     "flags": [],
     "updated": false,
     "new_fact": null,
     "due_src": null
    }
   ],
   "waiting": [
    {
     "id": "d7b0918b8f",
     "text": "Which photos do you plan to use in the Bayview case study? Lisa asked for the list with the draft (E14). No photo list exists in the pack; the reply draft in the outbox promises one; nothing has been sent.",
     "from": "priya",
     "re": "b68f7dc802",
     "due": "",
     "due_src": null
    }
   ],
   "handed": [],
   "done": [
    {
     "id": "b68f7dc802:send",
     "title": "SENT: Re: Case study",
     "due": "",
     "overdue": false,
     "status": "sent",
     "sources": [
      "E14",
      "C08"
     ],
     "notes": [
      "→ lisa.park@bayview-freight.example  ·  outbox/sent/20261024-1500-priya-reply-lisa-case-study.md"
     ],
     "flags": []
    }
   ],
   "superseded": [],
   "asked": 1
  }
 ],
 "outbox": [
  {
   "file": "outbox/deploy-alerts-known-facts.md",
   "sent": false,
   "kind": "md",
   "to": "",
   "subject": "facts",
   "sources": ""
  },
  {
   "file": "outbox/sent/20261024-1500-priya-reply-lisa-case-study.md",
   "sent": true,
   "kind": "md",
   "to": "lisa.park@bayview-freight.example",
   "subject": "Re: Case study",
   "sources": "E14, C08"
  },
  {
   "file": "outbox/sent/20261024-1500-dana-tom-call-reask-maria.md",
   "sent": true,
   "kind": "md",
   "to": "maria.gomez@northwind-cold.example",
   "subject": "New times for our next call with Tom",
   "sources": "E03, C01, L-ZAP-104"
  },
  {
   "file": "outbox/sent/20261024-1500-weilin-reply-ken-ips-vlan.md",
   "sent": true,
   "kind": "md",
   "to": "ken.ong@harborpoint.example",
   "subject": "Re: IP range for Tuesday 3 Nov install",
   "sources": "E04, E02"
  },
  {
   "file": "outbox/sent/20261024-1500-weilin-reply-raj-start-time.md",
   "sent": true,
   "kind": "md",
   "to": "Raj Kumar, Harbor Point (WhatsApp; no email address in pack)",
   "subject": "Re: Tuesday start time",
   "sources": "WA02, E02"
  },
  {
   "file": "outbox/sent/20261024-1500-sam-reply-maria-northwind.md",
   "sent": true,
   "kind": "md",
   "to": "maria.gomez@northwind-cold.example",
   "subject": "Re: Dock cameras",
   "sources": "E15, E03, C01, L-ZAP-101"
  },
  {
   "file": "outbox/sent/20261024-1500-sam-reply-jordan-monday.md",
   "sent": true,
   "kind": "md",
   "to": "jordan.lee@mail.example",
   "subject": "Re: Monday?",
   "sources": "E06, C04"
  },
  {
   "file": "outbox/20261024-1500-dana-reschedule-crestline-call.md",
   "sent": false,
   "kind": "md",
   "to": "farah.aziz@crestline-dc.example",
   "subject": "Our call on Tue 3 Nov",
   "sources": "C03, E05, CAL01, CAL02"
  },
  {
   "file": "outbox/20261024-1500-priya-onepager-brief-northwind.md",
   "sent": false,
   "kind": "md",
   "to": "",
   "subject": "onepager-brief-northwind",
   "sources": ""
  },
  {
   "file": "outbox/20261024-1500-priya-onepager-brief-crestline.md",
   "sent": false,
   "kind": "md",
   "to": "",
   "subject": "onepager-brief-crestline",
   "sources": ""
  },
  {
   "file": "outbox/20261024-1500-sam-northwind-pricing-brief.md",
   "sent": false,
   "kind": "md",
   "to": "",
   "subject": "northwind-pricing-brief",
   "sources": ""
  },
  {
   "file": "outbox/.gitkeep",
   "sent": false,
   "kind": "",
   "to": "",
   "subject": ".gitkeep",
   "sources": ""
  }
 ],
 "questions": [
  {
   "to": "sam",
   "from": "sam",
   "text": "What customer price should Northwind (Maria) be quoted for the 12-door dock cameras? The pack only has supplier cost (\"Attached quote: 12 x OX-4K dome, $4,680 total [fictional]. 2-week lead time. Need a PO by Tue 27 Oct to hold stock. 50% upfront.\", E10), not a sell price. Brief is in the outbox."
  },
  {
   "to": "sam",
   "from": "sam",
   "text": "Approve reimbursing Wei Lin? \"Wei Lin paid $640 out of pocket for the Harbor Point site trip. Needs Sam's approval to reimburse.\" (C10, ZAP-160). Nothing will be paid without your approval; test mode only."
  },
  {
   "to": "weilin",
   "from": "weilin",
   "text": "Does the quoted camera match your layout? Optix quote Q-1182: \"Attached quote: 12 x OX-4K dome, $4,680 total [fictional]. 2-week lead time. Need a PO by Tue 27 Oct to hold stock. 50% upfront.\" (E10). You have not seen it (C09). Sam needs to know before the PO (due Tue 27 Oct)."
  },
  {
   "to": "dana",
   "from": "dana",
   "text": "Send the reschedule draft to Farah? Wei Lin is double-booked: Harbor Point Yard install 2026-11-03 14:00-16:30 vs Crestline Data Centers call 2026-11-03 15:00-15:45 (SGT). Draft is in the outbox; nothing has been sent."
  },
  {
   "to": "sam",
   "from": "sam",
   "text": "Rachel wants 2 customer references by Wed 28 Oct (C06). Only one pilot customer (Bayview) appears in the pack. Who is the second reference, and has each customer given permission?"
  },
  {
   "to": "sam",
   "from": "sam",
   "text": "What ballpark price range should Omar at Ridgeline get? He asked to get budget (E09). The pack has no Ridgeline price."
  },
  {
   "to": "weilin",
   "from": "weilin",
   "text": "Can the Harbor Point install start at 13:30 instead of 14:00? Raj asked (WA02); forklifts move at 16:00. The reply draft in the outbox commits no time; nothing has been sent."
  },
  {
   "to": "weilin",
   "from": "weilin",
   "text": "Ken asks: \"Do you need a VLAN?\" (E04). The pack does not say. What should the reply tell him? The draft in the outbox confirms the IPs and says you will answer; nothing has been sent."
  },
  {
   "to": "dana",
   "from": "dana",
   "text": "Who from Zapdemo attends the Ridgeline site visit on Tuesday or Wednesday morning? Omar asked (E09). The pack does not say who goes; Wei Lin is the engineer."
  },
  {
   "to": "priya",
   "from": "priya",
   "text": "Which photos do you plan to use in the Bayview case study? Lisa asked for the list with the draft (E14). No photo list exists in the pack; the reply draft in the outbox promises one; nothing has been sent."
  },
  {
   "to": "sam",
   "from": "sam",
   "text": "Where should Jordan go on Monday morning? He asked (E06) and no office address or location exists anywhere in the pack. The reply draft in the outbox says you will confirm; nothing has been sent."
  }
 ]
};
