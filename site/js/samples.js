// Demonstration data. Every outlet, headline and summary here is invented.
// `relevant` is the answer a human reader would give: is this story about the
// invented brief (reefs, mangroves, coastal fishing) or not? The board uses it
// to label false alarms and misses.

export const SAMPLE_WATCHLIST = `coral bleaching
mangrove | mangroves | mikoko
marine protected area | hifadhi ya bahari
octopus closure
sea turtle | kasa
seagrass
eel
tuna
Kilwa
Pemba Channel`;

export const CLIPPINGS = [
  {
    outlet: 'The Coastal Courier', kind: 'Daily', lang: 'en', relevant: true,
    headline: 'Kilwa fishers vote to extend octopus closure',
    summary: 'Three villages will keep their reef flats shut for a further three months.',
  },
  {
    outlet: 'Gazeti la Mwambao', kind: 'Gazeti', lang: 'sw', relevant: true,
    headline: 'Mikoko elfu kumi yapandwa Delta ya Rufiji',
    summary: 'Vikundi vya wanawake vimepanda miche katika eneo lililoharibiwa na mafuriko.',
  },
  {
    outlet: 'Bahari Wire', kind: 'Wire', lang: 'en', relevant: true,
    headline: 'CORAL BLEACHING ALERT FOR PEMBA CHANNEL AS SEA WARMS',
    summary: 'DIVERS REPORT PALE CORAL ON THE OUTER REEF. SURVEY TEAMS SAIL THURSDAY.',
  },
  {
    outlet: 'The Monsoon Standard', kind: 'Daily', lang: 'en', relevant: false,
    headline: 'Steel prices rise for a third month',
    summary: 'Builders say reinforcing bar costs more again, and wheel importers feel the pinch.',
  },
  {
    outlet: 'Radio Kusi', kind: 'Redio', lang: 'sw', relevant: false,
    headline: 'Mikasa ya barabarani yaongezeka msimu wa mvua',
    summary: 'Polisi wawataka madereva kupunguza mwendo katika barabara za pwani.',
  },
  {
    outlet: 'Sauti ya Mwambao', kind: 'Redio', lang: 'sw', relevant: true,
    headline: 'Kasa wa kijani warejea ufukweni baada ya miaka kumi',
    summary: 'Wanakijiji wanalinda viota usiku kucha hadi mayai yaanguliwe.',
  },
  {
    outlet: 'The Dhow Dispatch', kind: 'Weekly', lang: 'en', relevant: true,
    headline: 'New marine-protected area gazetted south of the delta',
    summary: 'The boundary takes in two islands and the channel between them.',
  },
  {
    outlet: 'Jahazi Forum', kind: 'Forum thread', lang: 'sw', relevant: false,
    headline: 'Tuna matumaini makubwa na timu yetu Jumamosi',
    summary: 'Mashabiki wajadili kikosi kabla ya mechi ya mwisho wa wiki.',
  },
  {
    outlet: '@pwani_notebook', kind: 'Social post', lang: 'en', relevant: true,
    headline: 'Seagrass meadows off the north coast mapped for the first time',
    summary: 'Six weeks, two small boats and a borrowed drone. Thread follows. #BahariYetu',
  },
  {
    outlet: 'Habari za Kaskazi', kind: 'Gazeti', lang: 'sw', relevant: true,
    headline: 'Wavuvi wadogo waomba Hifadhi ya Bahari ilindwe',
    summary: 'Wasema boti kubwa zinaingia eneo lililotengwa nyakati za usiku.',
  },
  {
    outlet: 'The Lighthouse Post', kind: 'Daily', lang: 'en', relevant: false,
    headline: 'Harbour dredging put back until March',
    summary: 'The port authority says the contractor’s barge is still under repair.',
  },
  {
    outlet: 'The Coastal Courier', kind: 'Daily', lang: 'en', relevant: true,
    headline: 'Sea turtles tagged at Kilwa turn up 900 km south',
    summary: 'A satellite tag fitted last year has been tracing one animal’s route.',
  },
];
