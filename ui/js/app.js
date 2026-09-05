const searchInput=$("searchInput");
const searchTestament=$("searchTestament");
const searchResults=$("searchResults");
const searchEmpty=$("searchEmpty");
const stage=$("stage"), liveDot=$("liveDot"), liveTxt=$("liveTxt");
const popoutBtn=$("popoutBtn"), clearBtn=$("clearBtn");
const recallFeed=$("recallFeed"), recallEmpty=$("recallEmpty");
const jsonFeed=$("jsonFeed");
const saveBtn=$("saveBtn"), connBanner=$("connBanner"), actionToast=$("actionToast");
const startupBar=$("startupBar"), startupTitle=$("startupTitle");
const startupProgressBar=$("startupProgressBar"), startupPct=$("startupPct");
const startupMsgStage=$("startupMsgStage"), startupCurrentMsg=$("startupCurrentMsg");
const micStatusPill=$("micStatusPill");
const liveBottomDock=$("liveBottomDock");
const refBook=$("refBook"), refChapter=$("refChapter"), refVerse=$("refVerse");
const refGoBtn=$("refGoBtn"), navPrevBtn=$("navPrevBtn"), navNextBtn=$("navNextBtn");
const previewStrip=$("previewStrip"), previewBody=$("previewBody"), broadcastBtn=$("broadcastBtn");
const previewTag=$("previewTag");
const bookOptions=$("bookOptions");
const browserBooks=$("browserBooks"), browserChapters=$("browserChapters");
const browserVerses=$("browserVerses"), browserVersesHdr=$("browserVersesHdr");
const browserBookFilter=$("browserBookFilter");
const browserPrevBtn=$("browserPrevBtn"), browserNextBtn=$("browserNextBtn");
const browserGridBack=$("browserGridBack"), browserGridHdr=$("browserGridHdr");
const stagePrevBtn=$("stagePrevBtn"), stageNextBtn=$("stageNextBtn");
const browserBroadcastBtn=$("browserBroadcastBtn");
const micRing=() => txEmpty.querySelector(".mic-ring");
const micEmptyText=() => txEmpty.querySelector("p");
const vmixWsDot=$("vmixWsDot"), vmixWsTxt=$("vmixWsTxt");
const vmixWinDot=$("vmixWinDot"), vmixWinTxt=$("vmixWinTxt");
const vmixDbDot=$("vmixDbDot"), vmixDbTxt=$("vmixDbTxt");
const vmixOpenBtn=$("vmixOpenBtn");
const secondaryOrderRow=$("secondaryOrderRow"), secondaryBelow=$("secondaryBelow"), secondaryAbove=$("secondaryAbove"), secondaryOrderLang=$("secondaryOrderLang");
const ndiPreviewBtn=$("ndiPreviewBtn"), ndiPreviewStatus=$("ndiPreviewStatus");
const sidebar=$("sidebar"), mainGrid=$("mainGrid"), logFeed=$("logFeed");
const logBadge=$("logBadge"), headerLogDot=$("headerLogDot"), navLogs=$("navLogs");
const micProgress=$("micProgress"), micProgressBar=$("micProgressBar");
const clearLogsBtn=$("clearLogsBtn"), copyLogsBtn=$("copyLogsBtn");
const versionPill=$("versionPill");
const micDeviceList=$("micDeviceList");
const copyJsonBtn=$("copyJsonBtn");
const gotoRecallBtn=$("gotoRecallBtn");

let txLines = 0, dets = 0, projectorWin = null;
let sessionLines = [];
let everConnected = false;
let backendReady = false;
let voiceKeywordsRequested = false;

// Detection & voice toggles are persisted server-side, so the UI only
// mirrors them: change → send → the server echoes detection_state back.
const VOICE_TOGGLES = {
  transcriptAutoBroadcast: "transcript_auto_broadcast",
  voiceNavEnabled: "voice_nav_enabled",
  voiceNavAutoBroadcast: "voice_nav_auto_broadcast",
  voiceNavWrapBooks: "voice_nav_wrap_books",
  voiceNavRespectsStory: "voice_nav_respects_story_mode",
};
Object.entries(VOICE_TOGGLES).forEach(([id, key]) => {
  const el = $(id);
  if (!el) return;
  el.onchange = () => {
let structureRequested = false;
let bookView = "list";                 // grid (abbreviation boxes) | list
let gridMode = "books";                // books -> chapters -> verses, in one pane
let gridChapters = [], gridVerses = [];

function ensureBibleStructure() {