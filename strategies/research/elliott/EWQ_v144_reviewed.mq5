//+------------------------------------------------------------------+
//| EWQ_v144.mq5 - Elliott Quant PRO v14.4 (Production Ready)        |
//| 5 Optimizations: PushPivot, CollectTrades, VerifySubWaves,       |
//| AnalyzeCurrentChart, ComputeAltRun - all use chunked growth      |
//+------------------------------------------------------------------+
#property copyright "EWQ"
#property version "14.4"
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots 0

#define EWQ_VER "14.4"
#define MAX_TF 12
#define MAX_PTS 12
#define MAX_HIST 500000
#define MAX_NODES 256
#define MAX_CACHE 30000
#define MAX_LEGS 8
#define MIN_BUILD 3000
#define MAX_SCENARIOS 8
#define CHUNK_MIN 64
#define CHUNK_INIT 256

enum EAUTO{AUTO_OFF=0,AUTO_PRESET=1,AUTO_VOLATILITY=2,AUTO_HYBRID=3};
input EAUTO InpAutoMode=AUTO_HYBRID;
input int InpAutoVolBars=200;
input int InpChartBars=0;
input int InpMTFBars=800;
input int InpATRPeriod=14;
input double InpPivotMult=1.80;
input int InpMaxChartPivots=20000;
input int InpMaxMTFPivots=100;
input double InpMinScore=35.0;
input int InpRefreshSec=60;
input int InpConfirmDelay=0;
input double InpMinEntryScore=60.0;
input double InpMinSubScore=50.0;
input bool InpRequireSubwaves=true;
input double InpMinRR=1.0;
input bool InpUseATRTradeStop=false;
input double InpTradeStopATR=1.50;
input int InpMaxEntryAgeBars=3;
input int InpHorizonBars=60;
input double InpMinPatternScore=25.0;
input bool InpAutoScanStep=true;
input bool InpStrictFibonacci=true;
input bool InpEnforceChanneling=true;
input double InpChannelTolerance=0.03;
input bool InpUseVolumeConfirm=false;
input bool InpEnforceAlternation=true;
input bool InpEnforceTimeDegree=true;
input bool InpCheckTriangleInner=true;
input bool InpUseFibCluster=true;
input bool InpUseMomentumDiv=true;
input int InpRSIPeriod=14;
input bool InpUseFVG=true;
input bool InpUseCandleConfirm=true;
input bool InpCheckW4Depth=true;
input bool InpCheckW5Truncation=true;
input bool InpCheckDiagPosition=true;
input double InpW5TruncMaxPct=5.0;
input bool InpFilterSessions=false;
input int InpMinSpreadPoints=0;
input int InpNewsBlackoutMin=0;
input bool InpHTFBiasFilter=false;
input int InpHTFBiasTF=1440;
input bool InpEnableCombos=true;
input bool InpEnableTriple=true;
input bool InpEnableDiamond=true;
input bool InpEnableRunTri=true;
input bool InpEnableFailed5=true;
input bool InpAlternationV2=true;
input double InpAltWeightDepth=0.40;
input double InpAltWeightTime=0.30;
input double InpAltWeightForm=0.30;
input bool InpUseHierarchy=true;
input double InpHierMinScore=50.0;
input bool InpShowHistory=true;
input bool InpShowSkeleton=false;
input bool InpShowHistoryLabels=false;
input bool InpShowCurrent=true;
input bool InpShowCurrentLabels=true;
input bool InpShowGapFillers=true;
input int InpLineWidth=2;
input bool InpShowFuture=true;
input bool InpAutoShift=true;
input double InpShiftPercent=42.0;
input int InpProjectionBars=32;
input bool InpShowTP1=true;
input bool InpShowTP2=true;
input bool InpShowTP3=true;
input bool InpShowInvalidation=true;
input bool InpShowEntryLabel=true;
input int InpMaxWavesDrawn=5000;
input int InpScanStep=1;
input bool InpLogSignals=false;
input string InpLogFileName="EWQ_v144_signals.csv";
input int InpWFBarsCount=3000;
input int InpWFInSamplePct=70;
input bool InpRunWFOnStart=false;
input bool InpShowDashV14=true;
input bool InpDashRight=true;
input int InpDashX=10;
input int InpDashY=62;
input int InpBtnX=10;
input int InpBtnY=30;
input int InpBtnW=180;
input int InpBtnH=26;
input bool InpAlertsEnabled=false;
input bool InpAlertPopup=true;
input bool InpAlertSound=false;
input string InpAlertSoundFile="alert.wav";
input bool InpAlertPush=false;
input int InpAlertCooldown=300;
input bool InpUseTelegram=false;
input string InpTelegramToken="";
input string InpTelegramChatID="";
input color ClrImpulse=C'0,210,255';
input color ClrDiagonal=C'255,50,170';
input color ClrCorrection=C'255,80,70';
input color ClrTriangle=C'195,110,255';
input color ClrCurrent=C'255,255,0';
input color ClrFuture=C'140,170,50';
input color ClrSkeleton=C'70,75,85';
input color ClrTP1=C'0,255,120';
input color ClrTP2=C'0,210,255';
input color ClrTP3=C'220,100,255';
input color ClrHistImpulse=C'0,150,230';
input color ClrHistCorrection=C'255,90,75';
input color ClrBuyEntry=C'0,255,100';
input color ClrSellEntry=C'255,50,50';
input color ClrDiamond=C'255,180,100';
input color ClrRunTri=C'180,255,100';
input color ClrFailed5=C'255,100,180';
input color ClrInvalid=C'255,65,65';
input color ClrSL=C'255,80,80';

enum EPAT{P_NONE=0,P_IMPULSE,P_EXTENSION,P_TRUNCATION,P_DIAG_LEAD,P_DIAG_END,P_DIAG_GENERIC,P_ZIGZAG,P_FLAT_REG,P_FLAT_EXP,P_FLAT_RUN,P_TRI_CONT,P_TRI_BAR,P_TRI_EXP,P_SWING,P_WXY,P_WXYXZ,P_DIAMOND,P_TRI_RUN,P_FAILED_5};
enum EALIGN{A_NONE=0,A_GREEN,A_GOLD,A_RED,A_GRAY};
enum ESIGMODE{SM_CONFIRMED=0,SM_WATCH=1,SM_NOT_READY=2};

struct Pivot{datetime time;double price;int bar;bool isHigh;bool prov;int confirmedBar;datetime confirmedTime;long volume;};
struct Candidate{bool valid;EPAT pat;int dir,preDir,s,e,n;bool trunc,ext;int extW;double sStruct,sSub,sFib,sAlt,sChan,sPers,sTime,sVol,sDegree,sInner,sMomentum;double composite;bool hardRules;double sAlt2;double channelErr;bool channelOK,volumeOK,alternationOK,degreeOK,innerOK,w4DepthOK,w5TruncOK;double fibClusterScore;EPAT wPat,xPat,yPat;int legs;double failedPct;bool isRunning;bool isDiamond;double patternQuality;};
struct WaveNode{long id,parent;long children[MAX_LEGS];int childCount;ENUM_TIMEFRAMES tf;EPAT pattern;int dir;double compositeScore;EALIGN align;double alignScore;bool fitsInParent;double structuralFit;};
struct Analy{bool avail;ENUM_TIMEFRAMES tf;EPAT pat;int dir,futDir,preDir;double quality,entry;datetime readyTime;int readyBar;bool active,structureValid,qualified;string state;double atr;bool trunc,ext;int extW;bool prov;int pc;Pivot pivots[MAX_PTS];double basis,tp1,tp2,tp3,inval,tradeSL;double sStruct,sSub,sFib,sAlt,sChan,sPers,sTime,sVol,sDegree,sInner,sMomentum;double composite;bool hardRules;EALIGN align;double alignScore,hierConf,deepHier;double sAlt2;bool isCombination;int comboLegs;double failedPct;bool isRunning;bool isDiamond;double patternQuality;double channelErr;bool channelOK,volumeOK,alternationOK,degreeOK,innerOK;double fibClusterScore;int scenarioRank;};
struct PivCache{bool ready;datetime stamp;Pivot pivots[];int count;double atr;};
struct Consensus{int dominantDir;double weightedAgree;int confirmCount,divergeCount,neutralCount;ENUM_TIMEFRAMES domTF;double domStrength;bool tradeReady;EALIGN overallAlign;};
struct SigItem{double price;string text;color clr;int fs;};
struct AssetProfile{string className,classCode;double pivotMult;int atrPeriod;double minRR,minScore;color badgeColor;};
struct CorrCache{bool valid;Candidate corr;};
struct Scenario{Candidate cand;double score;string label;};
struct WFTrade{datetime t;double r;bool win;bool valid;double entry,sl,tp;};
struct WFResultX{double isWinRate,oosWinRate,isProfitFactor,oosProfitFactor,consistency;int tradesIS,tradesOOS;bool valid;};
struct BootstrapCI{double lower,upper,mean;};
struct MonteCarloResult{double avgFinal,worstCase,bestCase,avgDD;};

Analy g_chart,g_mtf[MAX_TF];
Consensus g_cons;
Pivot g_chartPiv[];
Candidate g_chartMap[];
PivCache g_cache[MAX_TF];
WaveNode g_tree[MAX_NODES];
int g_treeCount=0;long g_nextNodeId=1;
ENUM_TIMEFRAMES g_tfList[MAX_TF];int g_tfCount=0;
ENUM_TIMEFRAMES g_curTF=PERIOD_M15;
bool g_init=false,g_chartReady=false;
datetime g_lastBar=0,g_lastRefresh=0,g_seenClosed[MAX_TF],g_lastClosedBar=0;
bool g_busy=false,g_firstRun=true,g_oldShift=false;
double g_oldShiftSize=0;
string g_pfx="EWQ144_";
AssetProfile g_profile;
double g_activePivotMult=1.80,g_activeMinRR=1.0,g_activeMinScore=60.0;
double g_activeMinSub=50.0,g_activeHierMin=50.0;
int g_activeATRPeriod=14;
string g_lastSymbol="";
bool g_isOffline=false;
CorrCache g_corrCache[];
int g_corrCacheTot=0;
datetime g_corrCacheFirst=0,g_corrCacheLast=0;
ENUM_TIMEFRAMES g_corrCacheTF=PERIOD_CURRENT;
string g_corrCacheSym="";
int g_altRun[];int g_altRunTot=0;
uint g_altRunSigLo=0,g_altRunSigHi=0;
int g_tfNodeIdx[MAX_TF];
double g_cachedEMA21[MAX_TF],g_cachedEMA55[MAX_TF];
datetime g_cachedEMATime[MAX_TF];bool g_cachedEMAReady[MAX_TF];
double g_wStruct=0.22,g_wSub=0.12,g_wFib=0.18,g_wAlt=0.05;
double g_wAlt2=0.10,g_wChan=0.08,g_wPers=0.08,g_wTime=0.07;
double g_wVol=0.05,g_wDegree=0.03,g_wInner=0.02,g_wMom=0.05;
int g_hiSK=0,g_hiHist=0,g_hiHL=0,g_hiCur=0,g_hiCL=0,g_hiSigL=0,g_hiLink=0;
string g_lastLoggedState[MAX_TF];
bool g_logEnabled=false;
string g_logFileName="";
WFResultX g_wfResultX;
datetime g_lastAlertTime=0;
string g_lastAlertKey="";
string g_btnCycle="";
int g_dashMode=0;
bool g_dashVisState=true;
bool g_dashRightState=true;
uint g_lastClickTick=0;
string g_lastClickName="";

// Reusable buffers for hot paths (v14.4)
Pivot g_segBuffer[];
int g_segCap=0;

bool BestCand(const Pivot &p[],int tot,int s,int n,Candidate &best);
bool SelectBetterCandidate(const Candidate &c,Candidate &best);
bool BestCorrection(const Pivot &p[],int tot,int s,Candidate &out);
bool BestCorrectionCached(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalZigzag(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalFlat(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalImpulse(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalDiagonal(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalTriangle(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalWXY(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalWXYXZ(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalDiamond(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalRunningTriangle(const Pivot &p[],int tot,int s,Candidate &out);
bool EvalFailed5th(const Pivot &p[],int tot,int s,Candidate &out);
void RunScoring(Candidate &c,const Pivot &p[],ENUM_TIMEFRAMES tf);
void ComputeAltRun(const Pivot &p[],int tot);
bool Alternating(const Pivot &p[],int s,int n,int &dir);
void PrepareCorrCache(const Pivot &p[],int tot,ENUM_TIMEFRAMES tf);
bool CheckChanneling(const Pivot &p[],const Candidate &c,double &err);
bool CheckVolume(const Pivot &p[],const Candidate &c);
bool CheckAlternation(const Pivot &p[],const Candidate &c);
bool CheckTimeDegree(const Pivot &p[],const Candidate &c);
bool CheckTriangleInner(const Pivot &p[],const Candidate &c,ENUM_TIMEFRAMES tf);
bool CheckW4Depth(const Pivot &p[],const Candidate &c);
bool CheckW5Truncation(const Pivot &p[],const Candidate &c);
double ScoreFibCluster(const Pivot &p[],const Candidate &c);
string PatName(EPAT p);

double Clamp(double v,double a,double b){return v<a?a:(v>b?b:v);}
int Sgn(double v){return v>0.0?1:(v<0.0?-1:0);}
string CurFont(){return "Consolas";}
void PerfLog(string t,uint ms){if(false)PrintFormat("EWQ %s: %u ms",t,ms);}
int TFMinutes(ENUM_TIMEFRAMES tf){
   switch(tf){case PERIOD_M1:return 1;case PERIOD_M5:return 5;case PERIOD_M15:return 15;
   case PERIOD_M30:return 30;case PERIOD_H1:return 60;case PERIOD_H4:return 240;
   case PERIOD_D1:return 1440;case PERIOD_W1:return 10080;case PERIOD_MN1:return 43200;}
   return(int)(PeriodSeconds(tf)/60);
}
void SortTFList(){
   for(int i=0;i<g_tfCount-1;i++)
      for(int j=0;j<g_tfCount-1-i;j++)
         if(TFMinutes(g_tfList[j])>TFMinutes(g_tfList[j+1])){
            ENUM_TIMEFRAMES t=g_tfList[j];g_tfList[j]=g_tfList[j+1];g_tfList[j+1]=t;
         }
}
bool TFInList(ENUM_TIMEFRAMES tf){for(int i=0;i<g_tfCount;i++)if(g_tfList[i]==tf)return true;return false;}
void AddTFIfMissing(ENUM_TIMEFRAMES tf){if(TFInList(tf)||g_tfCount>=MAX_TF)return;g_tfList[g_tfCount]=tf;g_tfCount++;}
ENUM_TIMEFRAMES GetChartTF(){ENUM_TIMEFRAMES tf=(ENUM_TIMEFRAMES)ChartPeriod(0);if(tf==PERIOD_CURRENT)tf=(ENUM_TIMEFRAMES)_Period;return tf;}
void BuildTFList(){
   g_tfCount=0;
   AddTFIfMissing(PERIOD_M1);AddTFIfMissing(PERIOD_M5);AddTFIfMissing(PERIOD_M15);
   AddTFIfMissing(PERIOD_M30);AddTFIfMissing(PERIOD_H1);AddTFIfMissing(PERIOD_H4);
   AddTFIfMissing(PERIOD_D1);AddTFIfMissing(PERIOD_W1);AddTFIfMissing(PERIOD_MN1);
   ENUM_TIMEFRAMES ct=GetChartTF();if(!TFInList(ct))AddTFIfMissing(ct);
   SortTFList();
}
int TFIdx(ENUM_TIMEFRAMES tf){for(int i=0;i<g_tfCount;i++)if(g_tfList[i]==tf)return i;return -1;}
ENUM_TIMEFRAMES LowerTF(ENUM_TIMEFRAMES tf){int i=TFIdx(tf);if(i<=0)return tf;return g_tfList[i-1];}
string TFName(ENUM_TIMEFRAMES tf){
   switch(tf){case PERIOD_M1:return "M1";case PERIOD_M5:return "M5";case PERIOD_M15:return "M15";
   case PERIOD_M30:return "M30";case PERIOD_H1:return "H1";case PERIOD_H4:return "H4";
   case PERIOD_D1:return "D1";case PERIOD_W1:return "W1";case PERIOD_MN1:return "MN";}
   return EnumToString(tf);
}
double TFWeight(int i){
   if(i<0||i>=g_tfCount)return 1.0;
   int mins=TFMinutes(g_tfList[i]);
   double l=MathLog((double)MathMax(1,mins))/MathLog(2.0);
   double w=1.0+l*0.65;if(w>11.0)w=11.0;return w;
}
string DetectAssetClass(){
   string sym=_Symbol;StringToUpper(sym);
   if(StringFind(sym,"BTC")>=0||StringFind(sym,"ETH")>=0||StringFind(sym,"SOL")>=0)return "Crypto";
   if(StringFind(sym,"XAU")>=0||StringFind(sym,"GOLD")>=0)return "Gold";
   if(StringFind(sym,"XAG")>=0||StringFind(sym,"SILVER")>=0)return "Silver";
   if(StringFind(sym,"XPT")>=0||StringFind(sym,"PLATINUM")>=0)return "Platinum";
   if(StringFind(sym,"XPD")>=0)return "Palladium";
   if(StringFind(sym,"USOIL")>=0||StringFind(sym,"WTI")>=0)return "Energy";
   if(StringFind(sym,"US30")>=0||StringFind(sym,"NAS")>=0||StringFind(sym,"US100")>=0)return "Index";
   string known[20]={"USD","EUR","GBP","JPY","AUD","NZD","CAD","CHF","SEK","NOK","DKK","ZAR","TRY","MXN","SGD","HKD","CNH","PLN","HUF","CZK"};
   string majors[8]={"USD","EUR","GBP","JPY","CHF","CAD","AUD","NZD"};
   int p1=-1;string c1="";
   for(int i=0;i<20;i++){int pos=StringFind(sym,known[i]);if(pos>=0&&(p1<0||pos<p1)){p1=pos;c1=known[i];}}
   if(p1<0)return "Generic";
   int p2=-1;string c2="";
   for(int i=0;i<20;i++){if(known[i]==c1)continue;int pos=StringFind(sym,known[i]);if(pos>=0&&(p2<0||pos<p2)){p2=pos;c2=known[i];}}
   if(p2<0)return "Generic";
   bool m1=false,m2=false;
   for(int i=0;i<8;i++){if(c1==majors[i])m1=true;if(c2==majors[i])m2=true;}
   return(m1&&m2)?"Forex Major":"Forex Cross";
}
AssetProfile GetPresetForClass(string cls){
   AssetProfile p;p.className=cls;p.badgeColor=clrGray;
   if(cls=="Forex Major"){p.classCode="FX-M";p.pivotMult=1.00;p.atrPeriod=14;p.minRR=1.5;p.minScore=55.0;}
   else if(cls=="Forex Cross"){p.classCode="FX-X";p.pivotMult=1.20;p.atrPeriod=14;p.minRR=1.3;p.minScore=55.0;}
   else if(cls=="Gold"){p.classCode="XAU";p.pivotMult=1.40;p.atrPeriod=20;p.minRR=1.5;p.minScore=60.0;}
   else if(cls=="Silver"||cls=="Platinum"||cls=="Palladium"){p.classCode="MET";p.pivotMult=1.50;p.atrPeriod=20;p.minRR=1.5;p.minScore=60.0;}
   else if(cls=="Energy"){p.classCode="OIL";p.pivotMult=1.60;p.atrPeriod=20;p.minRR=1.5;p.minScore=60.0;}
   else if(cls=="Index"){p.classCode="IDX";p.pivotMult=1.30;p.atrPeriod=14;p.minRR=1.5;p.minScore=55.0;}
   else if(cls=="Crypto"){p.classCode="CRY";p.pivotMult=2.00;p.atrPeriod=20;p.minRR=2.0;p.minScore=65.0;}
   else{p.classCode="GEN";p.pivotMult=1.20;p.atrPeriod=14;p.minRR=1.0;p.minScore=55.0;}
   return p;
}
double VolatilityFactor(ENUM_TIMEFRAMES tf,int bars){
   MqlRates r[];int n=CopyRates(_Symbol,tf,0,MathMax(50,bars),r);
   if(n<50)return 1.0;
   double s=0;int c=0;
   for(int i=0;i<n;i++){double hi=r[i].high,lo=r[i].low,cl=r[i].close;if(cl<=0)continue;s+=(hi-lo)/cl;c++;}
   if(c==0)return 1.0;
   double a=s/c;
   if(a<0.0005)return 0.80;if(a<0.0010)return 0.90;if(a<0.0020)return 1.00;
   if(a<0.0035)return 1.15;if(a<0.0060)return 1.30;if(a<0.0120)return 1.45;
   return 1.60;
}
void ApplyAutoProfile(bool logIt){
   g_activePivotMult=InpPivotMult;g_activeATRPeriod=InpATRPeriod;
   g_activeMinRR=InpMinRR;g_activeMinScore=InpMinEntryScore;
   g_activeMinSub=InpMinSubScore;g_activeHierMin=InpHierMinScore;
   string cls=DetectAssetClass();AssetProfile p=GetPresetForClass(cls);
   double volF=1.0;
   if(InpAutoMode==AUTO_VOLATILITY||InpAutoMode==AUTO_HYBRID){
      volF=VolatilityFactor(GetChartTF(),InpAutoVolBars);
      p.pivotMult=Clamp(p.pivotMult*volF,0.80,4.00);p.pivotMult=NormalizeDouble(p.pivotMult,2);
   }
   g_profile=p;
   if(InpAutoMode==AUTO_OFF){if(logIt)PrintFormat("EWQ: OFF %s",p.className);return;}
   g_activePivotMult=p.pivotMult;g_activeATRPeriod=p.atrPeriod;
   g_activeMinRR=p.minRR;g_activeMinScore=p.minScore;
   if(cls=="Crypto"){g_activeMinSub=55.0;g_activeHierMin=55.0;}
   else if(cls=="Forex Major"){g_activeMinSub=50.0;g_activeHierMin=50.0;}
   if(logIt)PrintFormat("EWQ v%s: %s volF=%.2f Pivot=%.2f MinScore=%.0f",EWQ_VER,p.className,volF,p.pivotMult,p.minScore);
}
bool IsImpulse(EPAT p){return p==P_IMPULSE||p==P_EXTENSION||p==P_TRUNCATION;}
bool IsDiagonal(EPAT p){return p==P_DIAG_LEAD||p==P_DIAG_END||p==P_DIAG_GENERIC;}
bool IsMotive(EPAT p){return IsImpulse(p)||IsDiagonal(p);}
bool IsFlat(EPAT p){return p==P_FLAT_REG||p==P_FLAT_EXP||p==P_FLAT_RUN;}
bool IsTriangle(EPAT p){return p==P_TRI_CONT||p==P_TRI_BAR||p==P_TRI_EXP||p==P_TRI_RUN;}
bool IsCorrection(EPAT p){return p==P_ZIGZAG||IsFlat(p)||p==P_DIAMOND;}
bool IsCombination(EPAT p){return p==P_WXY||p==P_WXYXZ;}
bool IsAdvanced(EPAT p){return p==P_DIAMOND||p==P_TRI_RUN||p==P_FAILED_5||p==P_WXY||p==P_WXYXZ;}
string TrendName(int d){if(d>0)return "UP";if(d<0)return "DOWN";return "NEUTRAL";}
string AlignText(EALIGN a){
   if(a==A_GREEN)return "ENTRY";if(a==A_GOLD)return "WAIT";
   if(a==A_RED)return "CONFLICT";return "NEUTRAL";
}
string PatName(EPAT p){
   switch(p){case P_IMPULSE:return "Impulse";case P_EXTENSION:return "Extension";
   case P_TRUNCATION:return "Trunc";case P_DIAG_LEAD:return "LeadDiag";
   case P_DIAG_END:return "EndDiag";case P_DIAG_GENERIC:return "Diag";
   case P_ZIGZAG:return "Zigzag";case P_FLAT_REG:return "Flat";
   case P_FLAT_EXP:return "ExpFlat";case P_FLAT_RUN:return "RunFlat";
   case P_TRI_CONT:return "TriCont";case P_TRI_BAR:return "TriBar";
   case P_TRI_EXP:return "TriExp";case P_SWING:return "Swing";
   case P_WXY:return "W-X-Y";case P_WXYXZ:return "W-X-Y-X-Z";
   case P_DIAMOND:return "Diamond";case P_TRI_RUN:return "RunTri";
   case P_FAILED_5:return "Fail5th";}
   return "-";
}
int MinBars(ENUM_TIMEFRAMES tf){
   if(tf==PERIOD_MN1)return 20;if(tf==PERIOD_W1)return 30;
   if(tf==PERIOD_D1)return 50;return 80;
}
bool LoadRates(ENUM_TIMEFRAMES tf,int limit,MqlRates &rates[],int &cnt){
   cnt=0;int mn=MinBars(tf);int av=Bars(_Symbol,tf);
   if(av<mn)return false;
   int req=(limit<=0)?av:MathMin(limit,av);
   if(req<mn)req=mn;if(req>MAX_HIST)req=MAX_HIST;
   ArraySetAsSeries(rates,false);
   int c=CopyRates(_Symbol,tf,1,req,rates);
   if(c<mn)return false;cnt=c;return true;
}
bool BuildATR(const MqlRates &r[],int cnt,double &atr[]){
   if(cnt<2)return false;
   ArrayResize(atr,cnt);
   int p=MathMax(2,g_activeATRPeriod);
   for(int i=0;i<cnt;i++){
      double tr=r[i].high-r[i].low;
      if(i>0){double hg=MathAbs(r[i].high-r[i-1].close);double lg=MathAbs(r[i].low-r[i-1].close);if(hg>tr)tr=hg;if(lg>tr)tr=lg;}
      if(i==0)atr[i]=tr;
      else if(i<p)atr[i]=(atr[i-1]*(double)i+tr)/(double)(i+1);
      else atr[i]=(atr[i-1]*(double)(p-1)+tr)/(double)p;
   }
   return true;
}
// v14.4 OPTIMIZED: Geometric growth for PushPivot
void PushPivot(Pivot &arr[],const Pivot &p){
   // ArraySize is the logical count, not capacity. Reserve spare memory via
   // ArrayResize's third argument so unused slots never become fake pivots.
   int c=ArraySize(arr);
   if(c>0&&arr[c-1].isHigh==p.isHigh){
      bool rep=(p.isHigh&&p.price>arr[c-1].price)||(!p.isHigh&&p.price<arr[c-1].price);
      if(rep)arr[c-1]=p;
      return;
   }
   if(ArrayResize(arr,c+1,CHUNK_INIT)<0){Print("EWQ: pivot allocation failed");return;}
   arr[c]=p;
}
// v14.4 OPTIMIZED: Pre-allocated g_altRun
void ComputeAltRun(const Pivot &p[],int tot){
   if(tot<=0){ArrayResize(g_altRun,0);g_altRunTot=0;g_altRunSigLo=0;g_altRunSigHi=0;return;}
   uint sl=(uint)(p[0].time^(long)(p[0].price*100000));
   uint sh=(uint)(p[tot-1].time^(long)(p[tot-1].price*100000));
   // Recompute: equal endpoints do not prove equal interior pivot sequences.
   // Keep the logical length equal to tot; extra reserve remains invisible.
   if(ArrayResize(g_altRun,tot,CHUNK_INIT)<0){g_altRunTot=0;Print("EWQ: alternation allocation failed");return;}
   g_altRunTot=tot;g_altRunSigLo=sl;g_altRunSigHi=sh;
   g_altRun[tot-1]=1;
   if(tot>=2){int d=Sgn(p[tot-1].price-p[tot-2].price);g_altRun[tot-2]=(d!=0)?2:1;}
   for(int i=tot-3;i>=0;i--){
      int d1=Sgn(p[i+1].price-p[i].price);
      if(d1==0){g_altRun[i]=1;continue;}
      int d2=Sgn(p[i+2].price-p[i+1].price);
      if(d2!=0&&d1!=d2)g_altRun[i]=g_altRun[i+1]+1;
      else g_altRun[i]=2;
   }
}
bool Alternating(const Pivot &p[],int s,int n,int &dir){
   dir=0;
   if(n<2||s<0)return false;
   if(g_altRunTot!=ArraySize(g_altRun)||s+n>g_altRunTot)return false;
   dir=Sgn(p[s+1].price-p[s].price);
   if(dir==0)return false;
   return(g_altRun[s]>=n);
}
bool BuildPivots(const MqlRates &r[],const double &atr[],int cnt,double mult,Pivot &out[]){
   ArrayResize(out,0);
   if(cnt<20)return false;
   double hi=r[0].high,lo=r[0].low;
   long volHi=r[0].tick_volume,volLo=r[0].tick_volume;
   int hiI=0,loI=0,dir=0;
   for(int i=1;i<cnt;i++){
      double thr=MathMax(atr[i-1]*mult,_Point*5.0);
      if(dir==0){
         if(r[i].close-lo>=thr&&loI<i){
            Pivot p;p.time=r[loI].time;p.price=lo;p.bar=loI;p.isHigh=false;p.prov=false;
            p.confirmedBar=i;p.confirmedTime=r[i].time;p.volume=volLo;
            PushPivot(out,p);dir=1;hi=r[i].high;hiI=i;volHi=r[i].tick_volume;
         }else if(hi-r[i].close>=thr&&hiI<i){
            Pivot p;p.time=r[hiI].time;p.price=hi;p.bar=hiI;p.isHigh=true;p.prov=false;
            p.confirmedBar=i;p.confirmedTime=r[i].time;p.volume=volHi;
            PushPivot(out,p);dir=-1;lo=r[i].low;loI=i;volLo=r[i].tick_volume;
         }else{
            if(r[i].high>hi){hi=r[i].high;hiI=i;volHi=r[i].tick_volume;}
            if(r[i].low<lo){lo=r[i].low;loI=i;volLo=r[i].tick_volume;}
         }
      }else if(dir>0){
         if(r[i].high>hi){hi=r[i].high;hiI=i;volHi=r[i].tick_volume;}
         if(hiI<i&&hi-r[i].close>=thr){
            Pivot p;p.time=r[hiI].time;p.price=hi;p.bar=hiI;p.isHigh=true;p.prov=false;
            p.confirmedBar=i;p.confirmedTime=r[i].time;p.volume=volHi;
            PushPivot(out,p);dir=-1;lo=r[i].low;loI=i;volLo=r[i].tick_volume;
         }
      }else{
         if(r[i].low<lo){lo=r[i].low;loI=i;volLo=r[i].tick_volume;}
         if(loI<i&&r[i].close-lo>=thr){
            Pivot p;p.time=r[loI].time;p.price=lo;p.bar=loI;p.isHigh=false;p.prov=false;
            p.confirmedBar=i;p.confirmedTime=r[i].time;p.volume=volLo;
            PushPivot(out,p);dir=1;hi=r[i].high;hiI=i;volHi=r[i].tick_volume;
         }
      }
   }
   int n=ArraySize(out);
   if(n>=4)ComputeAltRun(out,n);
   return n>=4;
}
bool BuildAdaptivePivots(const MqlRates &r[],const double &atr[],int cnt,int maxP,Pivot &out[]){
   if(!BuildPivots(r,atr,cnt,g_activePivotMult,out))return false;
   int n=ArraySize(out);
   if(maxP>=1000)return true;
   int keep=MathMax(6,maxP);
   if(n>keep){
      for(int i=0;i<keep;i++)out[i]=out[n-keep+i];
      ArrayResize(out,keep);ComputeAltRun(out,keep);
   }
   return ArraySize(out)>=4;
}
void ResetCand(Candidate &c){
   c.valid=false;c.pat=P_NONE;c.dir=0;c.preDir=0;c.s=0;c.e=0;c.n=0;
   c.trunc=false;c.ext=false;c.extW=0;
   c.sStruct=0;c.sSub=0;c.sFib=0;c.sAlt=0;c.sChan=0;c.sPers=0;c.sTime=0;
   c.sVol=0;c.sDegree=0;c.sInner=0;c.sMomentum=50.0;
   c.composite=0;c.hardRules=false;c.sAlt2=50.0;
   c.channelErr=0;c.channelOK=false;
   c.volumeOK=false;c.alternationOK=false;c.degreeOK=false;c.innerOK=false;
   c.w4DepthOK=true;c.w5TruncOK=true;c.fibClusterScore=0;
   c.wPat=P_NONE;c.xPat=P_NONE;c.yPat=P_NONE;c.legs=0;
   c.failedPct=0;c.isRunning=false;c.isDiamond=false;c.patternQuality=0;
}
void ResetAnaly(Analy &a,ENUM_TIMEFRAMES tf){
   a.avail=false;a.tf=tf;a.pat=P_NONE;a.dir=0;a.futDir=0;a.preDir=0;
   a.quality=0;a.entry=0;a.readyTime=0;a.readyBar=-1;
   a.active=false;a.structureValid=false;a.qualified=false;a.state="NO DATA";
   a.atr=0;a.trunc=false;a.ext=false;a.extW=0;a.prov=false;a.pc=0;
   a.basis=0;a.tp1=0;a.tp2=0;a.tp3=0;a.inval=0;a.tradeSL=0;
   a.sStruct=0;a.sSub=0;a.sFib=0;a.sAlt=0;a.sChan=0;a.sPers=0;a.sTime=0;
   a.sVol=0;a.sDegree=0;a.sInner=0;a.sMomentum=50.0;
   a.composite=0;a.hardRules=false;
   a.align=A_NONE;a.alignScore=0;a.hierConf=40.0;a.deepHier=0;
   a.sAlt2=50.0;a.isCombination=false;a.comboLegs=0;
   a.failedPct=0;a.isRunning=false;a.isDiamond=false;a.patternQuality=0;
   a.channelErr=0;a.channelOK=false;
   a.volumeOK=false;a.alternationOK=false;a.degreeOK=false;a.innerOK=false;
   a.fibClusterScore=0;a.scenarioRank=0;
}
bool CheckChanneling(const Pivot &p[],const Candidate &c,double &err){
   err=1.0;
   if(!IsImpulse(c.pat)||c.n<6)return false;
   if(c.s+3>=ArraySize(p))return false;
   int b0=p[c.s].bar,b2=p[c.s+2].bar,b3=p[c.s+3].bar;
   if(b2==b0||b3==b0)return false;
   double slope=(p[c.s+2].price-p[c.s].price)/(double)(b2-b0);
   double proj=p[c.s+1].price+slope*(double)(b3-p[c.s+1].bar);
   double w3=MathAbs(p[c.s+3].price-p[c.s+2].price);
   if(w3<=_Point)return false;
   err=MathAbs(p[c.s+3].price-proj)/w3;
   return(err<=InpChannelTolerance);
}
bool CheckVolume(const Pivot &p[],const Candidate &c){
   if(!InpUseVolumeConfirm)return true;
   if(!IsImpulse(c.pat)||c.n<6)return true;
   if(c.s+5>=ArraySize(p))return true;
   long v1=0,v3=0;
   for(int i=c.s;i<c.s+2;i++)v1+=p[i].volume;
   for(int i=c.s+2;i<c.s+4;i++)v3+=p[i].volume;
   if(v1<=0||v3<=0)return true;
   return(v3>v1);
}
bool CheckAlternation(const Pivot &p[],const Candidate &c){
   if(!InpEnforceAlternation)return true;
   if(!IsImpulse(c.pat)||c.n<6)return true;
   if(c.s+5>=ArraySize(p))return true;
   double w1=MathAbs(p[c.s+1].price-p[c.s].price);
   double w3=MathAbs(p[c.s+3].price-p[c.s+2].price);
   if(w1<=0||w3<=0)return true;
   double r2=MathAbs(p[c.s+2].price-p[c.s+1].price)/w1;
   double r4=MathAbs(p[c.s+4].price-p[c.s+3].price)/w3;
   double dD=MathAbs(r2-r4)/MathMax(r2,r4);
   int t2=MathAbs(p[c.s+2].bar-p[c.s+1].bar);
   int t4=MathAbs(p[c.s+4].bar-p[c.s+3].bar);
   if(t2<1)t2=1;if(t4<1)t4=1;
   double tR=(double)MathMax(t2,t4)/(double)MathMin(t2,t4);
   return(dD>0.20||tR>1.50);
}
bool CheckTimeDegree(const Pivot &p[],const Candidate &c){
   if(!InpEnforceTimeDegree)return true;
   if(!IsImpulse(c.pat)||c.n<6)return true;
   if(c.s+5>=ArraySize(p))return true;
   int t1=MathAbs(p[c.s+1].bar-p[c.s].bar);
   int t3=MathAbs(p[c.s+3].bar-p[c.s+2].bar);
   int t5=MathAbs(p[c.s+5].bar-p[c.s+4].bar);
   if(t1<1||t3<1||t5<1)return true;
   double avg=(t1+t3+t5)/3.0;
   if(avg<2.0)return true;
   double d1=MathAbs(t1-avg)/avg,d3=MathAbs(t3-avg)/avg,d5=MathAbs(t5-avg)/avg;
   double mx=MathMax(d1,MathMax(d3,d5));
   return(mx<1.0);
}
bool CheckTriangleInner(const Pivot &p[],const Candidate &c,ENUM_TIMEFRAMES tf){
   if(!InpCheckTriangleInner)return true;
   if(!IsTriangle(c.pat))return true;
   ENUM_TIMEFRAMES lt=LowerTF(tf);int li=TFIdx(lt);
   if(lt==tf||li<0||!g_cache[li].ready)return true;
   int count=g_cache[li].count;
   if(count<6)return true;
   int twc=0,legs=c.n-1;
   for(int leg=0;leg<legs;leg++){
      datetime ts=p[c.s+leg].time,te=p[c.s+leg+1].time;
      int inner=0;
      for(int j=0;j<count;j++)if(g_cache[li].pivots[j].time>ts&&g_cache[li].pivots[j].time<te)inner++;
      if(inner>=2)twc++;
   }
   return(twc>=legs-1);
}
bool CheckW4Depth(const Pivot &p[],const Candidate &c){
   if(!InpCheckW4Depth)return true;
   if(!IsImpulse(c.pat)||c.n<6)return true;
   if(c.s+5>=ArraySize(p))return true;
   double w3=MathAbs(p[c.s+3].price-p[c.s+2].price);
   double w4=MathAbs(p[c.s+4].price-p[c.s+3].price);
   if(w3<=0)return true;
   double r4=w4/w3;
   return(r4>=0.146&&r4<=0.500);
}
bool CheckW5Truncation(const Pivot &p[],const Candidate &c){
   if(!InpCheckW5Truncation)return true;
   if(!IsImpulse(c.pat)||c.n<6)return true;
   if(c.s+5>=ArraySize(p))return true;
   bool tr=(c.dir>0)?(p[c.s+5].price<p[c.s+3].price):(p[c.s+5].price>p[c.s+3].price);
   if(!tr)return true;
   double w3=MathAbs(p[c.s+3].price-p[c.s+2].price);
   if(w3<=0)return true;
   double sf=MathAbs(p[c.s+3].price-p[c.s+5].price);
   double pct=(sf/w3)*100.0;
   return(pct<=InpW5TruncMaxPct);
}
double ScoreFibCluster(const Pivot &p[],const Candidate &c){
   if(!InpUseFibCluster)return 50.0;
   if(!IsImpulse(c.pat)||c.n<6)return 50.0;
   if(c.s+5>=ArraySize(p))return 50.0;
   double w1=MathAbs(p[c.s+1].price-p[c.s].price);
   double w3=MathAbs(p[c.s+3].price-p[c.s+2].price);
   if(w1<=0||w3<=0)return 50.0;
   double fibs[]={0.236,0.382,0.500,0.618,0.786,1.0,1.272,1.618,2.618};
   int len=ArraySize(fibs),cl=0;
   for(int i=0;i<len;i++)
      for(int j=0;j<len;j++){
         double v1=w1*fibs[i],v2=w3*fibs[j];
         if(MathMax(v1,v2)>0&&MathAbs(v1-v2)/MathMax(v1,v2)<0.02)cl++;
      }
   if(cl>=4)return 100.0;if(cl>=3)return 85.0;if(cl>=2)return 70.0;if(cl>=1)return 55.0;
   return 30.0;
}
double ComputeRSI(const MqlRates &r[],int cnt,int period,int atBar){
   if(cnt<period+2||atBar<period+1||atBar>=cnt)return 50.0;
   double g=0,l=0;
   for(int i=atBar-period+1;i<=atBar;i++){double d=r[i].close-r[i-1].close;if(d>0)g+=d;else l-=d;}
   if(l==0)return 100.0;
   return 100.0-100.0/(1.0+g/l);
}
double ScoreMomentumDivergence(const Pivot &p[],const Candidate &c,const MqlRates &r[],int cnt){
   if(!InpUseMomentumDiv)return 50.0;
   if(!IsImpulse(c.pat)||c.n<6)return 50.0;
   if(c.s+5>=ArraySize(p))return 50.0;
   int r3=-1,r5=-1;
   for(int i=0;i<cnt;i++){if(r[i].time==p[c.s+3].time)r3=i;if(r[i].time==p[c.s+5].time)r5=i;}
   if(r3<0||r5<0)return 50.0;
   double rsi3=ComputeRSI(r,cnt,InpRSIPeriod,r3);
   double rsi5=ComputeRSI(r,cnt,InpRSIPeriod,r5);
   double pr3=p[c.s+3].price,pr5=p[c.s+5].price;
   int d=c.dir;double sc=50.0;
   if(d>0){
      if(pr5>pr3&&rsi5<rsi3){double rd=rsi3-rsi5;sc=(rd>=10)?100.0:((rd>=5)?80.0:65.0);}
      else if(pr5>pr3&&rsi5>rsi3)sc=75.0;
   }else{
      if(pr5<pr3&&rsi5>rsi3){double rd=rsi5-rsi3;sc=(rd>=10)?100.0:((rd>=5)?80.0:65.0);}
      else if(pr5<pr3&&rsi5<rsi3)sc=75.0;
   }
   return sc;
}
int CountFVGinRange(const MqlRates &r[],int cnt,double lo,double hi,int dir){
   if(!InpUseFVG)return 0;
   int count=0;
   for(int i=2;i<cnt-1;i++){
      double fL=0,fH=0;bool found=false;
      if(dir>0&&r[i].low>r[i-2].high){fL=r[i-2].high;fH=r[i].low;found=true;}
      if(dir<0&&r[i].high<r[i-2].low){fL=r[i].high;fH=r[i-2].low;found=true;}
      if(!found)continue;
      if(fH>=lo&&fL<=hi)count++;
   }
   return count;
}
double ScoreFVG(Analy &a,const MqlRates &r[],int cnt){
   if(!InpUseFVG)return 50.0;
   if(a.tp1<=0)return 50.0;
   double lo=MathMin(a.entry,a.tp1),hi=MathMax(a.entry,a.tp1);
   int fvgs=CountFVGinRange(r,cnt,lo,hi,a.futDir);
   if(fvgs>=3)return 100.0;if(fvgs==2)return 80.0;if(fvgs==1)return 60.0;
   return 40.0;
}
double ScoreCandleConfirm(const Pivot &p,const MqlRates &r[],int cnt,int dir){
   if(!InpUseCandleConfirm)return 50.0;
   int rIdx=-1;
   for(int i=0;i<cnt;i++){if(r[i].time==p.time){rIdx=i;break;}}
   if(rIdx<1)return 50.0;
   double body=MathAbs(r[rIdx].close-r[rIdx].open);
   double range=r[rIdx].high-r[rIdx].low;
   if(range<=_Point)return 50.0;
   double up=r[rIdx].high-MathMax(r[rIdx].close,r[rIdx].open);
   double dn=MathMin(r[rIdx].close,r[rIdx].open)-r[rIdx].low;
   double bp=body/range;double sc=50.0;
   if(bp<0.35){
      if(dir>0&&dn>up*2.0)sc=95.0;
      else if(dir<0&&up>dn*2.0)sc=95.0;
   }
   if(rIdx>=1){
      double pb=MathAbs(r[rIdx-1].close-r[rIdx-1].open);
      if(body>pb*1.3){
         bool be=(r[rIdx].close>r[rIdx].open)&&(r[rIdx-1].close<r[rIdx-1].open);
         bool se=(r[rIdx].close<r[rIdx].open)&&(r[rIdx-1].close>r[rIdx-1].open);
         if(dir>0&&be)sc=MathMax(sc,90.0);
         if(dir<0&&se)sc=MathMax(sc,90.0);
      }
   }
   return sc;
}
EPAT DetectDiagonalPosition(const Pivot &p[],const Candidate &c,ENUM_TIMEFRAMES tf){
   if(!IsDiagonal(c.pat))return c.pat;
   if(!InpCheckDiagPosition)return c.pat;
   if(c.s<2)return P_DIAG_GENERIC;
   double pm=MathAbs(p[c.s].price-p[c.s-1].price);
   double pr=MathAbs(p[c.s+5].price-p[c.s].price);
   if(pr<=0)return P_DIAG_GENERIC;
   double ratio=pm/pr;
   if(ratio>1.5)return P_DIAG_END;
   if(ratio<0.5)return P_DIAG_LEAD;
   return P_DIAG_GENERIC;
}
bool EvalImpulse(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+5>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<6)return false;
   int dir=0;if(!Alternating(p,s,6,dir))return false;
   Pivot p0=p[s],p1=p[s+1],p2=p[s+2],p3=p[s+3],p4=p[s+4],p5=p[s+5];
   double w1=MathAbs(p1.price-p0.price),w2=MathAbs(p2.price-p1.price);
   double w3=MathAbs(p3.price-p2.price),w4=MathAbs(p4.price-p3.price);
   double w5=MathAbs(p5.price-p4.price);
   if(w1<=0||w2<=0||w3<=0||w4<=0||w5<=0)return false;
   if(dir>0){
      if(p2.price<=p0.price)return false;if(p3.price<=p1.price)return false;
      if(p4.price<=p1.price)return false;if(p4.price<=p2.price)return false;
   }else{
      if(p2.price>=p0.price)return false;if(p3.price>=p1.price)return false;
      if(p4.price>=p1.price)return false;if(p4.price>=p2.price)return false;
   }
   double mn=MathMin(w1,w5);if(w3<mn)return false;
   bool trunc=(dir>0)?(p5.price<p3.price):(p5.price>p3.price);
   if(trunc&&w5<w1*0.10)return false;
   bool ext=false;int extW=0;double thr=1.38;
   if(w1>=w3&&w1>=w5&&w1>=MathMax(w3,w5)*thr){ext=true;extW=1;}
   else if(w3>=w1&&w3>=w5&&w3>=MathMax(w1,w5)*thr){ext=true;extW=3;}
   else if(w5>=w1&&w5>=w3&&w5>=MathMax(w1,w3)*thr){ext=true;extW=5;}
   double r2=w2/w1,r3=w3/w1,r4=w4/w3,r5=w5/w1;
   double sc=50.0;
   if(InpStrictFibonacci){
      if(r2>=0.500&&r2<=0.618)sc+=22.0;else if(r2>=0.382&&r2<=0.786)sc+=12.0;else sc-=8.0;
      if((r3>=1.518&&r3<=1.718)||(r3>=2.468&&r3<=2.768))sc+=25.0;
      else if(r3>=1.382&&r3<=2.000)sc+=12.0;else if(r3>=2.000&&r3<=3.000)sc+=10.0;else sc-=10.0;
      if(r4>=0.236&&r4<=0.382)sc+=22.0;else if(r4>=0.146&&r4<=0.500)sc+=10.0;else sc-=6.0;
      bool w5eqw1=(MathAbs(r5-1.0)<0.05);
      bool w5fib=(r5>=0.618&&r5<=1.618)||(r5>=1.618&&r5<=2.618);
      if(w5eqw1)sc+=20.0;else if(w5fib)sc+=15.0;else sc+=5.0;
   }else{
      if(r2>=0.382&&r2<=0.786)sc+=10.0;
      if(r3>=1.0&&r3<=2.618)sc+=10.0;
      if(r4>=0.236&&r4<=0.618)sc+=8.0;
      if(!ext&&r5>=0.75&&r5<=1.30)sc+=5.0;
   }
   if(ext)sc+=5.0;if(trunc)sc-=8.0;
   out.valid=true;
   if(trunc)out.pat=P_TRUNCATION;else if(ext)out.pat=P_EXTENSION;else out.pat=P_IMPULSE;
   out.dir=dir;out.s=s;out.e=s+5;out.n=6;
   out.trunc=trunc;out.ext=ext;out.extW=extW;
   out.sStruct=Clamp(sc,0,100);
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   double chE=0;out.channelOK=CheckChanneling(p,out,chE);out.channelErr=chE;
   out.volumeOK=CheckVolume(p,out);
   out.alternationOK=CheckAlternation(p,out);
   out.degreeOK=CheckTimeDegree(p,out);
   out.w4DepthOK=CheckW4Depth(p,out);
   out.w5TruncOK=CheckW5Truncation(p,out);
   return true;
}
bool EvalDiagonal(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+5>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<6)return false;
   int dir=0;if(!Alternating(p,s,6,dir))return false;
   Pivot p0=p[s],p1=p[s+1],p2=p[s+2],p3=p[s+3],p4=p[s+4],p5=p[s+5];
   double w1=MathAbs(p1.price-p0.price),w2=MathAbs(p2.price-p1.price);
   double w3=MathAbs(p3.price-p2.price),w4=MathAbs(p4.price-p3.price);
   double w5=MathAbs(p5.price-p4.price);
   if(w1<=0||w2<=0||w3<=0||w4<=0||w5<=0)return false;
   if(dir>0){
      if(p2.price<=p0.price)return false;
      if(p4.price<=p1.price)return false;
      if(p3.price<=p1.price)return false;
   }else{
      if(p2.price>=p0.price)return false;
      if(p4.price>=p1.price)return false;
      if(p3.price>=p1.price)return false;
   }
   double mn=MathMin(w1,w5);if(w3<mn)return false;
   bool ov=(dir>0)?(p4.price<=p1.price):(p4.price>=p1.price);
   if(!ov)return false;
   bool co=(w3<w1)&&(w5<w3)&&(w4<w2);
   bool ex=(w3>w1)&&(w5>w3)&&(w4>w2);
   if(!co&&!ex)return false;
   double r2=w2/w1,r4=w4/w3;
   bool w2L=(r2>=0.66),w4L=(r4>=0.38);
   bool w2S=(r2>=0.66)&&(r2<=0.81),w4D=(r4>=0.38)&&(r4<=0.62);
   EPAT pat;double sc;
   if(co){if(w2L&&w4L){pat=P_DIAG_LEAD;sc=78.0;}else{pat=P_DIAG_GENERIC;sc=68.0;}}
   else{if(w2S&&w4D){pat=P_DIAG_END;sc=76.0;}else{pat=P_DIAG_GENERIC;sc=70.0;}}
   out.valid=true;out.pat=pat;out.dir=dir;
   out.s=s;out.e=s+5;out.n=6;
   out.sStruct=Clamp(sc,0,100);
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   out.channelOK=true;out.volumeOK=true;
   out.alternationOK=true;out.degreeOK=true;
   out.w4DepthOK=true;out.w5TruncOK=true;
   return true;
}
bool EvalZigzag(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+3>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<4)return false;
   int dir=0;if(!Alternating(p,s,4,dir))return false;
   double A=MathAbs(p[s+1].price-p[s].price);
   double B=MathAbs(p[s+2].price-p[s+1].price);
   double C=MathAbs(p[s+3].price-p[s+2].price);
   if(A<=0||B<=0||C<=0)return false;
   double rB=B/A,rC=C/A;
   if(rB<0.15||rB>=1.0)return false;
   if(rC<0.45||rC>2.80)return false;
   if(dir>0&&p[s+3].price<=p[s+1].price)return false;
   if(dir<0&&p[s+3].price>=p[s+1].price)return false;
   double sc=55.0;
   if(InpStrictFibonacci){
      if(rB>=0.568&&rB<=0.668)sc+=20.0;
      else if(rB>=0.500&&rB<=0.786)sc+=12.0;else sc+=5.0;
      if(MathAbs(rC-1.0)<0.05)sc+=22.0;
      else if(MathAbs(rC-1.618)<0.10)sc+=20.0;
      else if(rC>=0.90&&rC<=1.30)sc+=12.0;else sc+=5.0;
   }else{
      if(rB>=0.382&&rB<=0.786)sc+=12.0;
      if(rC>=0.90&&rC<=1.10)sc+=14.0;else if(rC>=0.618&&rC<=1.618)sc+=8.0;
   }
   out.valid=true;out.pat=P_ZIGZAG;out.dir=dir;
   out.s=s;out.e=s+3;out.n=4;
   out.sStruct=Clamp(sc,0,100);
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   return true;
}
bool EvalFlat(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+3>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<4)return false;
   int dir=0;if(!Alternating(p,s,4,dir))return false;
   double A=MathAbs(p[s+1].price-p[s].price);
   double B=MathAbs(p[s+2].price-p[s+1].price);
   double C=MathAbs(p[s+3].price-p[s+2].price);
   if(A<=0||B<=0||C<=0)return false;
   double rB=B/A,rC=C/A;
   if(rB<0.85||rB>1.618)return false;
   bool bB,cB;
   if(dir>0){bB=(p[s+2].price<p[s].price);cB=(p[s+3].price>p[s+1].price);}
   else{bB=(p[s+2].price>p[s].price);cB=(p[s+3].price<p[s+1].price);}
   EPAT pat;double sc=55.0;
   if(!bB&&!cB&&rB>=0.90&&rB<=1.10){
      pat=P_FLAT_REG;sc+=22.0;if(rC>=0.90&&rC<=1.10)sc+=18.0;
   }else if(bB&&cB&&rB>=1.10&&rB<=1.618){
      pat=P_FLAT_EXP;sc+=22.0;if(rC>=1.10&&rC<=1.618)sc+=15.0;
   }else if(bB&&!cB&&rB>=1.10&&rB<=1.618){
      pat=P_FLAT_RUN;sc+=10.0;if(rC>=0.60&&rC<=0.90)sc+=10.0;
   }else return false;
   out.valid=true;out.pat=pat;out.dir=dir;
   out.s=s;out.e=s+3;out.n=4;
   out.sStruct=Clamp(sc,0,100);
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   return true;
}
bool EvalTriangle(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+5>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<6)return false;
   double hi[3],lo[3];int hc=0,lc=0;
   for(int i=s;i<=s+5;i++){
      if(p[i].isHigh&&hc<3){hi[hc]=p[i].price;hc++;}
      if(!p[i].isHigh&&lc<3){lo[lc]=p[i].price;lc++;}
   }
   if(hc<3||lc<3)return false;
   double range=MathAbs(hi[0]-lo[0]);if(range<=_Point*20)return false;
   double tol=range*0.15;
   bool contHi=(hi[1]<hi[0])&&(hi[2]<hi[1]+tol);
   bool contLo=(lo[1]>lo[0])&&(lo[2]>lo[1]-tol);
   bool cont=contHi&&contLo;
   bool barHi=(MathAbs(hi[2]-hi[0])<=tol)&&(lo[1]>lo[0]);
   bool barLo=(MathAbs(lo[2]-lo[0])<=tol)&&(hi[1]<hi[0]);
   bool bar=barHi||barLo;
   bool ex=(hi[1]>hi[0])&&(hi[2]>hi[1])&&(lo[1]<lo[0])&&(lo[2]<lo[1]);
   EPAT pat;double sc;
   if(cont){pat=P_TRI_CONT;sc=78.0;}
   else if(bar){pat=P_TRI_BAR;sc=74.0;}
   else if(ex){pat=P_TRI_EXP;sc=70.0;}
   else return false;
   int t1=p[s+2].bar-p[s].bar;int t2=p[s+5].bar-p[s+3].bar;
   if(t1>0&&t2>0){
      double tr=(double)MathMax(t1,t2)/(double)MathMin(t1,t2);
      if(tr>3.5)sc-=12.0;else if(tr>=1.5)sc-=5.0;else sc+=5.0;
   }
   int preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   int inD=preDir;if(inD==0)inD=-Sgn(p[s+5].price-p[s+4].price);
   out.valid=true;out.pat=pat;out.dir=inD;out.preDir=preDir;
   out.s=s;out.e=s+5;out.n=6;
   out.sStruct=Clamp(sc,0,100);
   return true;
}
bool EvalWXY(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+6>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<7)return false;
   Candidate W;if(!BestCorrectionCached(p,tot,s,W))return false;
   if(W.n!=4||W.s!=s)return false;
   Candidate Y;if(!BestCorrectionCached(p,tot,s+4,Y))return false;
   if(Y.n!=4||Y.s!=s+4)return false;
   int wD=W.dir;int xD=Sgn(p[s+4].price-p[s+3].price);
   if(xD==wD)return false;
   if(Y.dir!=wD)return false;
   double wR=MathAbs(p[s+3].price-p[s].price);
   double xR=MathAbs(p[s+4].price-p[s+3].price);
   if(wR<=0)return false;
   double xRt=xR/wR;
   if(xRt<0.25||xRt>1.80)return false;
   double sc=62.0;
   bool sW=(W.pat==P_ZIGZAG),sY=(Y.pat==P_ZIGZAG);
   if(sW!=sY)sc+=15.0;else sc-=8.0;
   if(xRt>=0.5&&xRt<=1.0)sc+=10.0;
   else if(xRt>=1.0&&xRt<=1.618)sc+=5.0;
   out.valid=true;out.pat=P_WXY;out.dir=wD;
   out.s=s;out.e=s+6;out.n=7;out.legs=7;
   out.wPat=W.pat;out.yPat=Y.pat;
   out.sStruct=Clamp(sc,0,100);
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   return true;
}
bool EvalWXYXZ(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+10>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<11)return false;
   Candidate W,Y,Z;
   if(!BestCorrectionCached(p,tot,s,W))return false;
   if(W.n!=4||W.s!=s)return false;
   if(!BestCorrectionCached(p,tot,s+4,Y))return false;
   if(Y.n!=4||Y.s!=s+4)return false;
   if(!BestCorrectionCached(p,tot,s+8,Z))return false;
   if(Z.n!=4||Z.s!=s+8)return false;
   int wD=W.dir,yD=Y.dir,zD=Z.dir;
   if(yD==wD)return false;
   if(zD!=wD)return false;
   int x1D=Sgn(p[s+4].price-p[s+3].price);
   if(x1D==wD)return false;
   double sc=58.0;int sc2=0;
   if(W.pat==P_ZIGZAG)sc2++;
   if(Y.pat==P_ZIGZAG)sc2++;
   if(Z.pat==P_ZIGZAG)sc2++;
   if(sc2==1||sc2==2)sc+=15.0;else sc-=5.0;
   out.valid=true;out.pat=P_WXYXZ;out.dir=wD;
   out.s=s;out.e=s+10;out.n=11;out.legs=11;
   out.wPat=W.pat;out.yPat=Y.pat;
   out.sStruct=Clamp(sc,0,100);
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   return true;
}
bool EvalDiamond(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(!InpEnableDiamond)return false;
   if(s<0||s+5>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<6)return false;
   int dir=0;if(!Alternating(p,s,6,dir))return false;
   double high[3],low[3];int hc=0,lc=0;
   for(int i=s;i<=s+5;i++){
      if(p[i].isHigh&&hc<3){high[hc]=p[i].price;hc++;}
      if(!p[i].isHigh&&lc<3){low[lc]=p[i].price;lc++;}
   }
   if(hc<3||lc<3)return false;
   bool eH=(high[1]>high[0])&&(high[2]>high[1]);
   bool eL=(low[1]<low[0])&&(low[2]<low[1]);
   if(!eH||!eL)return false;
   double r1=high[1]-high[0],r2=high[2]-high[1];
   double r3=low[0]-low[1],r4=low[1]-low[2];
   if(r1<=0||r2<=0||r3<=0||r4<=0)return false;
   double hS=MathAbs(r1-r2)/MathMax(r1,r2);
   double lS=MathAbs(r3-r4)/MathMax(r3,r4);
   if(hS>0.60||lS>0.60)return false;
   double tr=MathMax(high[2],high[1])-MathMin(low[2],low[1]);
   if(tr<=_Point*20)return false;
   double sS=100.0*(1.0-(hS+lS)/2.0);
   int t1=p[s+2].bar-p[s].bar;int t2=p[s+5].bar-p[s+3].bar;
   double tSy=MathAbs(t1-t2)/(double)MathMax(1,MathMax(t1,t2));
   double tSc=100.0*(1.0-tSy);
   double sc=sS*0.5+70.0*0.2+tSc*0.3;
   out.valid=true;out.pat=P_DIAMOND;out.dir=dir;
   out.s=s;out.e=s+5;out.n=6;out.legs=6;
   out.isDiamond=true;
   out.sStruct=Clamp(sc,0,100);
   out.patternQuality=out.sStruct;
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   return true;
}
bool EvalRunningTriangle(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(!InpEnableRunTri)return false;
   if(s<0||s+4>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<5)return false;
   int dir=0;
   if(s>0)dir=Sgn(p[s].price-p[s-1].price);
   if(dir==0)return false;
   int cD=0;if(!Alternating(p,s,5,cD))return false;
   Pivot pA=p[s],pB=p[s+1],pC=p[s+2],pD=p[s+3],pE=p[s+4];
   bool isR=false;double bM=0;
   if(dir>0){
      if(pB.price>pA.price&&pC.price<pB.price&&pD.price>pC.price&&pE.price<pD.price){
         double rAB=pB.price-pA.price,rCD=pD.price-pC.price;
         if(rAB>0&&rCD>0){double ratio=rCD/rAB;if(ratio>=0.50&&ratio<=1.20){isR=true;bM=rAB/MathMax(_Point,pB.price-pC.price);}}
      }
   }else{
      if(pB.price<pA.price&&pC.price>pB.price&&pD.price<pC.price&&pE.price>pD.price){
         double rAB=pA.price-pB.price,rCD=pC.price-pD.price;
         if(rAB>0&&rCD>0){double ratio=rCD/rAB;if(ratio>=0.50&&ratio<=1.20){isR=true;bM=rAB/MathMax(_Point,pC.price-pB.price);}}
      }
   }
   if(!isR)return false;
   double sc=68.0;
   if(bM>=0.30&&bM<=0.70)sc+=12.0;else if(bM>0.70)sc+=8.0;else sc+=3.0;
   out.valid=true;out.pat=P_TRI_RUN;out.dir=dir;
   out.s=s;out.e=s+4;out.n=5;out.legs=5;
   out.isRunning=true;
   out.sStruct=Clamp(sc,0,100);
   out.patternQuality=out.sStruct;
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   return true;
}
bool EvalFailed5th(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(!InpEnableFailed5)return false;
   if(s<0||s+5>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<6)return false;
   int dir=0;if(!Alternating(p,s,6,dir))return false;
   Pivot p0=p[s],p1=p[s+1],p2=p[s+2],p3=p[s+3],p4=p[s+4],p5=p[s+5];
   double w1=MathAbs(p1.price-p0.price),w2=MathAbs(p2.price-p1.price);
   double w3=MathAbs(p3.price-p2.price),w4=MathAbs(p4.price-p3.price);
   double w5=MathAbs(p5.price-p4.price);
   if(w1<=0||w2<=0||w3<=0||w4<=0||w5<=0)return false;
   if(dir>0){
      if(p2.price<=p0.price)return false;if(p3.price<=p1.price)return false;
      if(p4.price<=p1.price)return false;if(p4.price<=p2.price)return false;
   }else{
      if(p2.price>=p0.price)return false;if(p3.price>=p1.price)return false;
      if(p4.price>=p1.price)return false;if(p4.price>=p2.price)return false;
   }
   bool tr=(dir>0)?(p5.price<p3.price):(p5.price>p3.price);
   if(!tr)return false;
   if(w5<w3*0.15)return false;
   double sf=MathAbs(p3.price-p5.price);
   double fp=(sf/w3)*100.0;
   if(fp<3.0||fp>45.0)return false;
   if(dir>0){if(p5.price<p4.price)return false;}
   else{if(p5.price>p4.price)return false;}
   double sc=60.0;
   if(fp>=8.0&&fp<=20.0)sc+=20.0;
   else if(fp>=5.0&&fp<=30.0)sc+=12.0;else sc+=5.0;
   double r5_3=w5/w3;
   if(r5_3>=0.55&&r5_3<=0.70)sc+=10.0;
   else if(r5_3>=0.35&&r5_3<=0.85)sc+=5.0;
   double r4=w4/w3;
   if(r4>=0.30&&r4<=0.55)sc+=8.0;
   out.valid=true;out.pat=P_FAILED_5;out.dir=dir;
   out.s=s;out.e=s+5;out.n=6;out.legs=6;
   out.trunc=true;out.failedPct=fp;
   out.sStruct=Clamp(sc,0,100);
   out.patternQuality=out.sStruct;
   out.preDir=(s>0)?Sgn(p[s].price-p[s-1].price):0;
   return true;
}
void PrepareCorrCache(const Pivot &p[],int tot,ENUM_TIMEFRAMES tf){
   if(tot<=0){ArrayResize(g_corrCache,0);g_corrCacheTot=0;g_corrCacheFirst=0;g_corrCacheLast=0;g_corrCacheTF=PERIOD_CURRENT;g_corrCacheSym="";return;}
   datetime f=p[0].time,l=p[tot-1].time;
   if(g_corrCacheSym==_Symbol&&g_corrCacheTot==tot&&g_corrCacheFirst==f&&g_corrCacheLast==l&&g_corrCacheTF==tf&&ArraySize(g_corrCache)==tot)return;
   ArrayResize(g_corrCache,tot);
   for(int i=0;i<tot;i++){g_corrCache[i].valid=false;ResetCand(g_corrCache[i].corr);}
   g_corrCacheTot=tot;g_corrCacheFirst=f;g_corrCacheLast=l;
   g_corrCacheTF=tf;g_corrCacheSym=_Symbol;
}
bool BestCorrection(const Pivot &p[],int tot,int s,Candidate &out){
   ResetCand(out);
   if(s<0||s+3>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<4)return false;
   Candidate zz,fl;
   bool oz=EvalZigzag(p,tot,s,zz),of=EvalFlat(p,tot,s,fl);
   if(!oz&&!of)return false;
   if(oz&&(!of||zz.sStruct>=fl.sStruct))out=zz;else out=fl;
   return true;
}
bool BestCorrectionCached(const Pivot &p[],int tot,int s,Candidate &out){
   if(s<0||s>=ArraySize(g_corrCache)||g_corrCacheTot!=tot||g_corrCacheTF==PERIOD_CURRENT||g_corrCacheSym!=_Symbol)
      return BestCorrection(p,tot,s,out);
   if(g_corrCache[s].valid){out=g_corrCache[s].corr;return true;}
   Candidate c;
   if(!BestCorrection(p,tot,s,c)){g_corrCache[s].valid=false;return false;}
   g_corrCache[s].valid=true;g_corrCache[s].corr=c;out=c;return true;
}
int PatternRank(EPAT p){
   if(p==P_FAILED_5)return 6;if(IsImpulse(p))return 6;
   if(p==P_DIAMOND)return 5;if(IsDiagonal(p))return 5;
   if(p==P_TRI_RUN)return 4;if(IsTriangle(p))return 3;
   if(p==P_WXY||p==P_WXYXZ)return 3;if(IsCorrection(p))return 2;
   return 1;
}
bool SelectBetterCandidate(const Candidate &c,Candidate &best){
   if(!c.valid)return false;
   if(!best.valid){best=c;return true;}
   double dc=c.composite,db=best.composite;
   if(dc>db+0.01){best=c;return true;}
   if(dc<db-0.01)return false;
   if(c.sStruct>best.sStruct+0.01){best=c;return true;}
   if(c.sStruct<best.sStruct-0.01)return false;
   if(c.sFib>best.sFib+0.01){best=c;return true;}
   if(c.sFib<best.sFib-0.01)return false;
   int rC=PatternRank(c.pat),rB=PatternRank(best.pat);
   if(rC>rB){best=c;return true;}
   if(rC<rB)return false;
   if(c.n<best.n){best=c;return true;}
   if(c.n>best.n)return false;
   if(c.s>best.s){best=c;return true;}
   return false;
}
bool BestCand(const Pivot &p[],int tot,int s,int n,Candidate &best){
   ResetCand(best);
   if(s<0||n<1||s+n-1>=tot)return false;
   if(g_altRunTot==ArraySize(g_altRun)&&g_altRun[s]<n)return false;
   Candidate c;
   if(n==6){
      if(EvalFailed5th(p,tot,s,c))SelectBetterCandidate(c,best);
      if(EvalDiamond(p,tot,s,c))SelectBetterCandidate(c,best);
      if(EvalImpulse(p,tot,s,c))SelectBetterCandidate(c,best);
      if(EvalDiagonal(p,tot,s,c))SelectBetterCandidate(c,best);
      if(EvalTriangle(p,tot,s,c))SelectBetterCandidate(c,best);
      if(InpEnableCombos){
         if(EvalWXY(p,tot,s,c))SelectBetterCandidate(c,best);
         if(InpEnableTriple){if(EvalWXYXZ(p,tot,s,c))SelectBetterCandidate(c,best);}
      }
      return best.valid;
   }
   if(n==5){if(EvalRunningTriangle(p,tot,s,c))SelectBetterCandidate(c,best);return best.valid;}
   if(n==4){if(BestCorrectionCached(p,tot,s,c))SelectBetterCandidate(c,best);return best.valid;}
   return false;
}
void MakeSwing(const Pivot &p[],int s,int e,Candidate &out){
   ResetCand(out);
   out.valid=true;out.pat=P_SWING;
   out.dir=Sgn(p[e].price-p[s].price);
   out.s=s;out.e=e;out.n=e-s+1;
   out.sStruct=30.0;out.composite=30.0;out.hardRules=false;
}
// v14.4 OPTIMIZED: Pre-allocated seg buffer with manual push
double VerifySubWavesTree(const Candidate &par,const Pivot &pp[],ENUM_TIMEFRAMES tf){
   ENUM_TIMEFRAMES lt=LowerTF(tf);int li=TFIdx(lt);
   if(lt==tf||li<0||!g_cache[li].ready)return -1.0;
   int count=g_cache[li].count,legs=par.n-1;
   if(count<4||legs<1)return -1.0;
   datetime ts0=pp[par.s].time,te0=pp[par.e].time;
   if(g_cache[li].pivots[0].time>ts0||g_cache[li].pivots[count-1].time<te0)return -1.0;
   double score=0;int okC=0;
   bool parTri=IsTriangle(par.pat),parAdv=IsAdvanced(par.pat);
   if(g_segCap<256){ArrayResize(g_segBuffer,256);g_segCap=256;}
   for(int leg=0;leg<legs;leg++){
      datetime ts=pp[par.s+leg].time,te=pp[par.s+leg+1].time;
      int loIdx=-1,hiIdx=-1;
      for(int j=0;j<count;j++){if(g_cache[li].pivots[j].time>ts){loIdx=j;break;}}
      if(loIdx<0)continue;
      for(int j=loIdx;j<count;j++){if(g_cache[li].pivots[j].time>=te){hiIdx=j;break;}}
      if(hiIdx<0)hiIdx=count;
      int sp=hiIdx-loIdx;if(sp<3)continue;
      int segN=1;g_segBuffer[0]=pp[par.s+leg];
      int step=MathMax(1,sp/30);
      for(int j=loIdx;j<hiIdx;j+=step){
         if(!g_cache[li].pivots[j].prov){
            if(segN>=g_segCap){g_segCap=g_segCap+128;ArrayResize(g_segBuffer,g_segCap);}
            if(segN>0&&g_segBuffer[segN-1].isHigh==g_cache[li].pivots[j].isHigh){
               bool rep=(g_cache[li].pivots[j].isHigh&&g_cache[li].pivots[j].price>g_segBuffer[segN-1].price)||(!g_cache[li].pivots[j].isHigh&&g_cache[li].pivots[j].price<g_segBuffer[segN-1].price);
               if(rep)g_segBuffer[segN-1]=g_cache[li].pivots[j];
            }else{g_segBuffer[segN++]=g_cache[li].pivots[j];}
         }
      }
      if(segN>0&&g_segBuffer[segN-1].isHigh==pp[par.s+leg+1].isHigh){
         bool rep=(pp[par.s+leg+1].isHigh&&pp[par.s+leg+1].price>g_segBuffer[segN-1].price)||(!pp[par.s+leg+1].isHigh&&pp[par.s+leg+1].price<g_segBuffer[segN-1].price);
         if(rep)g_segBuffer[segN-1]=pp[par.s+leg+1];
      }else{
         if(segN>=g_segCap){g_segCap=g_segCap+128;ArrayResize(g_segBuffer,g_segCap);}
         g_segBuffer[segN++]=pp[par.s+leg+1];
      }
      int n=segN;if(n<4)continue;
      bool motive;
      if(parTri)motive=false;
      else if(parAdv)motive=(leg%2==0);
      else motive=(IsImpulse(par.pat)&&leg%2==0)||(par.pat==P_ZIGZAG&&leg!=1)||(IsFlat(par.pat)&&leg==2);
      Candidate sub;bool ok=false;
      if(motive&&n>=6)ok=EvalImpulse(g_segBuffer,n,0,sub)||EvalDiagonal(g_segBuffer,n,0,sub);
      else if(!motive&&n>=4)ok=BestCorrection(g_segBuffer,n,0,sub);
      else if(!motive&&n>=6)ok=EvalTriangle(g_segBuffer,n,0,sub);
      if(ok){score+=sub.sStruct;okC++;}
   }
   if(okC<(legs*6+9)/10)return -1.0;
   return score/(double)okC;
}
double ScoreFib(const Candidate &c,const Pivot &p[]){
   if(IsImpulse(c.pat)&&c.n>=6){
      double w1=MathAbs(p[c.s+1].price-p[c.s].price);
      double w2=MathAbs(p[c.s+2].price-p[c.s+1].price);
      double w3=MathAbs(p[c.s+3].price-p[c.s+2].price);
      double w4=MathAbs(p[c.s+4].price-p[c.s+3].price);
      double w5=MathAbs(p[c.s+5].price-p[c.s+4].price);
      if(w1<=0)return 0;
      double sc=0,maxP=0;
      double r2=w2/w1;maxP+=25;
      if(InpStrictFibonacci){if(r2>=0.500&&r2<=0.618)sc+=25;else if(r2>=0.382&&r2<=0.786)sc+=15;else sc+=5;}
      else{if(r2>=0.382&&r2<=0.786)sc+=25;else if(r2>=0.236&&r2<=0.886)sc+=15;else sc+=5;}
      double r3=w3/w1;maxP+=25;
      if(InpStrictFibonacci){
         if(r3>=1.518&&r3<=1.718)sc+=25;else if(r3>=2.468&&r3<=2.768)sc+=25;
         else if(r3>=1.382&&r3<=2.100)sc+=15;else sc+=5;
      }else{if(r3>=1.618&&r3<=2.618)sc+=25;else if(r3>=1.0&&r3<1.618)sc+=18;else sc+=5;}
      if(w3>0){
         double r4=w4/w3;maxP+=25;
         if(InpStrictFibonacci){if(r4>=0.236&&r4<=0.382)sc+=25;else if(r4>=0.146&&r4<=0.500)sc+=15;else sc+=5;}
         else{if(r4>=0.236&&r4<=0.500)sc+=25;else if(r4>=0.146&&r4<=0.618)sc+=15;else sc+=5;}
      }
      double r5a=w5/w1;maxP+=25;
      if(InpStrictFibonacci){if(MathAbs(r5a-1.0)<0.05)sc+=25;else if(r5a>=0.618&&r5a<=1.618)sc+=18;else sc+=5;}
      else{double r5b=(w3>0)?w5/w3:0;if((r5a>=0.85&&r5a<=1.15)||(r5b>=0.55&&r5b<=0.70))sc+=25;else sc+=8;}
      return Clamp((sc/maxP)*100.0,0,100);
   }
   return -1.0;
}
double ScoreAlt(const Candidate &c,const Pivot &p[]){
   if(!IsImpulse(c.pat)||c.n<6)return -1.0;
   int i0=c.s;
   double w1=MathAbs(p[i0+1].price-p[i0].price);
   double w2=MathAbs(p[i0+2].price-p[i0+1].price);
   double w3=MathAbs(p[i0+3].price-p[i0+2].price);
   double w4=MathAbs(p[i0+4].price-p[i0+3].price);
   if(w1<=0||w3<=0)return 50.0;
   double r2=w2/w1,r4=w4/w3;
   int t2=MathMax(1,p[i0+2].bar-p[i0+1].bar);
   int t4=MathMax(1,p[i0+4].bar-p[i0+3].bar);
   double s2=r2/(double)t2,s4=r4/(double)t4;
   double ratio=MathMax(s2,s4)/MathMax(0.0001,MathMin(s2,s4));
   if(ratio>=2.5)return 100.0;if(ratio>=2.0)return 88.0;
   if(ratio>=1.5)return 72.0;if(ratio>=1.25)return 58.0;
   if(ratio>=1.05)return 42.0;return 25.0;
}
double ScoreChan(const Candidate &c,const Pivot &p[]){
   if(!IsImpulse(c.pat)||c.n<6)return -1.0;
   double err=0;
   if(!CheckChanneling(p,c,err))return 20.0;
   if(err<=0.01)return 100.0;if(err<=0.02)return 85.0;
   if(err<=0.03)return 70.0;if(err<=0.05)return 50.0;
   return 30.0;
}
double ScorePers(const Candidate &c,const Pivot &p[]){
   if(!IsMotive(c.pat)||c.n<6)return -1.0;
   int i0=c.s;
   double w1=MathAbs(p[i0+1].price-p[i0].price);
   double w3=MathAbs(p[i0+3].price-p[i0+2].price);
   double w5=MathAbs(p[i0+5].price-p[i0+4].price);
   int t1=MathMax(1,p[i0+1].bar-p[i0].bar);
   int t3=MathMax(1,p[i0+3].bar-p[i0+2].bar);
   int t5=MathMax(1,p[i0+5].bar-p[i0+4].bar);
   double v1=w1/(double)t1,v3=w3/(double)t3,v5=w5/(double)t5;
   double sc=50.0;
   if(v3>v1&&v3>v5)sc+=25.0;else if(v3>v1||v3>v5)sc+=12.0;else sc-=12.0;
   if(v3>0&&v5/v3<0.85)sc+=18.0;else if(v5>v3*1.20)sc-=8.0;
   return Clamp(sc,0,100);
}
double ScoreTime(const Candidate &c,const Pivot &p[]){
   if(c.n<4)return 50.0;
   double sc=50.0;
   if(IsMotive(c.pat)&&c.n>=6){
      int t2=MathMax(1,p[c.s+2].bar-p[c.s+1].bar);
      int t4=MathMax(1,p[c.s+4].bar-p[c.s+3].bar);
      double r24=(double)MathMax(t2,t4)/(double)MathMin(t2,t4);
      if(r24>=1.4)sc+=20.0;else if(r24>=1.15)sc+=10.0;else sc-=5.0;
   }
   return Clamp(sc,0,100);
}
double ScoreVolume(const Candidate &c,const Pivot &p[]){
   if(!InpUseVolumeConfirm)return 50.0;
   if(!IsImpulse(c.pat)||c.n<6)return 50.0;
   long v1=0,v3=0,v5=0;
   for(int i=c.s;i<c.s+2;i++)v1+=p[i].volume;
   for(int i=c.s+2;i<c.s+4;i++)v3+=p[i].volume;
   for(int i=c.s+4;i<c.s+6&&i<ArraySize(p);i++)v5+=p[i].volume;
   if(v1<=0||v3<=0)return 50.0;
   double r3=(double)v3/(double)v1;
   double r5=(v3>0)?(double)v5/(double)v3:1.0;
   double sc=50.0;
   if(r3>1.20)sc+=25.0;else if(r3>1.00)sc+=15.0;else sc-=15.0;
   if(r5<0.85)sc+=15.0;else if(r5>1.20)sc-=8.0;
   return Clamp(sc,0,100);
}
double ScoreDegree(const Candidate &c,const Pivot &p[]){
   if(!InpEnforceTimeDegree)return 50.0;
   if(!IsImpulse(c.pat)||c.n<6)return 50.0;
   int t1=MathAbs(p[c.s+1].bar-p[c.s].bar);
   int t3=MathAbs(p[c.s+3].bar-p[c.s+2].bar);
   int t5=MathAbs(p[c.s+5].bar-p[c.s+4].bar);
   if(t1<1||t3<1||t5<1)return 50.0;
   double avg=(t1+t3+t5)/3.0;
   double d1=MathAbs(t1-avg)/avg,d3=MathAbs(t3-avg)/avg,d5=MathAbs(t5-avg)/avg;
   double mx=MathMax(d1,MathMax(d3,d5));
   if(mx<0.20)return 100.0;if(mx<0.35)return 80.0;
   if(mx<0.50)return 60.0;if(mx<0.80)return 40.0;
   return 25.0;
}
double ScoreInner(const Candidate &c,const Pivot &p[]){
   if(!InpCheckTriangleInner)return 50.0;
   if(!IsTriangle(c.pat))return 50.0;
   return c.innerOK?100.0:30.0;
}
double AlternationScoreV2(const Pivot &p[],const Candidate &c){
   if(!InpAlternationV2)return 50.0;
   if(!IsImpulse(c.pat)||c.n<6)return -1.0;
   if(c.s+5>=ArraySize(p))return 50.0;
   Pivot p0=p[c.s],p1=p[c.s+1],p2=p[c.s+2],p3=p[c.s+3],p4=p[c.s+4];
   double w1=MathAbs(p1.price-p0.price),w2=MathAbs(p2.price-p1.price);
   double w3=MathAbs(p3.price-p2.price),w4=MathAbs(p4.price-p3.price);
   if(w1<=0||w3<=0)return 50.0;
   double r2=w2/w1,r4=w4/w3;
   double dSc;
   bool dp2=(r2>=0.5),dp4=(r4>=0.5);
   if(dp2!=dp4)dSc=100.0;
   else if(MathAbs(r2-r4)>0.30)dSc=80.0;
   else if(MathAbs(r2-r4)>0.15)dSc=60.0;else dSc=30.0;
   int t2=p2.bar-p1.bar,t4=p4.bar-p3.bar;
   if(t2<1)t2=1;if(t4<1)t4=1;
   double tR=(double)MathMax(t2,t4)/(double)MathMin(t2,t4);
   double tSc;
   if(tR>=2.0)tSc=100.0;else if(tR>=1.5)tSc=80.0;else if(tR>=1.2)tSc=60.0;else tSc=30.0;
   double rr2=0.0,rr4=0.0;
   if(w2>0)rr2=MathAbs(p2.price-p0.price)/w2;
   if(w4>0)rr4=MathAbs(p4.price-p2.price)/w4;
   bool s2=(rr2>0.7),s4=(rr4>0.7);
   double fSc=(s2!=s4)?100.0:40.0;
   return Clamp(dSc*InpAltWeightDepth+tSc*InpAltWeightTime+fSc*InpAltWeightForm,0,100);
}
void RunScoring(Candidate &c,const Pivot &p[],ENUM_TIMEFRAMES tf){
   c.sSub=VerifySubWavesTree(c,p,tf);
   c.sFib=ScoreFib(c,p);
   c.sAlt=ScoreAlt(c,p);
   c.sChan=ScoreChan(c,p);
   c.sPers=ScorePers(c,p);
   c.sTime=ScoreTime(c,p);
   c.sVol=ScoreVolume(c,p);
   c.sDegree=ScoreDegree(c,p);
   c.sInner=ScoreInner(c,p);
   c.hardRules=c.valid&&c.pat!=P_SWING;
   c.sAlt2=AlternationScoreV2(p,c);
   c.fibClusterScore=ScoreFibCluster(p,c);
   if(InpEnforceChanneling&&IsImpulse(c.pat)&&!c.channelOK)c.hardRules=false;
   if(InpEnforceAlternation&&IsImpulse(c.pat)&&!c.alternationOK)c.hardRules=false;
   if(InpCheckW4Depth&&IsImpulse(c.pat)&&!c.w4DepthOK)c.hardRules=false;
   if(InpCheckW5Truncation&&IsImpulse(c.pat)&&!c.w5TruncOK)c.hardRules=false;
   if(InpCheckTriangleInner&&IsTriangle(c.pat))c.innerOK=CheckTriangleInner(p,c,tf);
   else c.innerOK=true;
   double sMom=50.0;
   if(InpUseMomentumDiv&&IsImpulse(c.pat)&&c.n>=6){
      MqlRates rM[];int cntM=CopyRates(_Symbol,tf,1,500,rM);
      if(cntM>50){ArraySetAsSeries(rM,false);sMom=ScoreMomentumDivergence(p,c,rM,cntM);}
   }
   c.sMomentum=sMom;
   double wS=0,wV=0;
   wS+=g_wStruct;wV+=g_wStruct*c.sStruct;
   if(c.sSub>=0){wS+=g_wSub;wV+=g_wSub*c.sSub;}
   if(c.sFib>=0){wS+=g_wFib;wV+=g_wFib*c.sFib;}
   if(c.sAlt>=0){wS+=g_wAlt;wV+=g_wAlt*c.sAlt;}
   if(c.sAlt2>=0){wS+=g_wAlt2;wV+=g_wAlt2*c.sAlt2;}
   if(c.sChan>=0){wS+=g_wChan;wV+=g_wChan*c.sChan;}
   if(c.sPers>=0){wS+=g_wPers;wV+=g_wPers*c.sPers;}
   if(c.sTime>=0){wS+=g_wTime;wV+=g_wTime*c.sTime;}
   if(c.sVol>=0){wS+=g_wVol;wV+=g_wVol*c.sVol;}
   if(c.sDegree>=0){wS+=g_wDegree;wV+=g_wDegree*c.sDegree;}
   if(c.sInner>=0){wS+=g_wInner;wV+=g_wInner*c.sInner;}
   wS+=g_wMom;wV+=g_wMom*c.sMomentum;
   if(wS>0.0)c.composite=Clamp(wV/wS,0,100);else c.composite=0;
   if(c.pat==P_WXY)c.composite=MathMin(100.0,c.composite+3.0);
   if(c.pat==P_WXYXZ)c.composite=MathMin(100.0,c.composite+5.0);
   if(c.pat==P_DIAMOND)c.composite=MathMin(100.0,c.composite+6.0);
   if(c.pat==P_TRI_RUN)c.composite=MathMin(100.0,c.composite+4.0);
   if(c.pat==P_FAILED_5)c.composite=MathMin(100.0,c.composite+8.0);
   if(c.pat==P_SWING)c.composite=MathMin(c.composite,35.0);
   if(c.fibClusterScore>=85)c.composite=MathMin(100.0,c.composite+5.0);
   else if(c.fibClusterScore>=70)c.composite=MathMin(100.0,c.composite+3.0);
}
int FutureDir(EPAT p,int dir,int preDir){
   if(dir==0||p==P_NONE||p==P_SWING)return 0;
   if(IsDiagonal(p))return -dir;
   if(p==P_FAILED_5)return -dir;
   if(IsImpulse(p)||IsCorrection(p)||IsCombination(p))return -dir;
   if(p==P_TRI_RUN)return(preDir!=0)?preDir:dir;
   if(IsTriangle(p))return(preDir!=0)?preDir:dir;
   return 0;
}
void PrepareEMACache(ENUM_TIMEFRAMES tf,int idx){
   if(idx<0||idx>=MAX_TF)return;
   MqlRates r[];int cnt=CopyRates(_Symbol,tf,1,120,r);
   if(cnt<60){g_cachedEMAReady[idx]=false;return;}
   ArraySetAsSeries(r,true);
   double a21=2.0/22.0,a55=2.0/56.0;
   double e21=r[cnt-1].close,e55=r[cnt-1].close;
   for(int i=cnt-2;i>=0;i--){e21=a21*r[i].close+(1.0-a21)*e21;e55=a55*r[i].close+(1.0-a55)*e55;}
   g_cachedEMA21[idx]=e21;g_cachedEMA55[idx]=e55;
   g_cachedEMATime[idx]=iTime(_Symbol,tf,1);g_cachedEMAReady[idx]=true;
}
double CtxScoreFast(int tfIdx,int dir,double lastClose){
   if(tfIdx<0||!g_cachedEMAReady[tfIdx]||dir==0)return 50.0;
   double e21=g_cachedEMA21[tfIdx],e55=g_cachedEMA55[tfIdx];
   double sc=50.0;
   if(dir>0){sc+=(e21>e55)?20:-15;sc+=(lastClose>e21)?15:-10;}
   else{sc+=(e21<e55)?20:-15;sc+=(lastClose<e21)?15:-10;}
   return Clamp(sc,0,100);
}
void ComputeTargets(Analy &a){
   a.tp1=0;a.tp2=0;a.tp3=0;a.inval=0;a.tradeSL=0;a.basis=0;
   if(a.pc<4||a.futDir==0||a.readyBar<0)return;
   double org=a.entry;
   double lo=a.pivots[0].price,hi=lo;
   for(int i=1;i<a.pc;i++){lo=MathMin(lo,a.pivots[i].price);hi=MathMax(hi,a.pivots[i].price);}
   int d=a.futDir;
   double pad=MathMax(a.atr*0.25,_Point*5.0);
   if(IsImpulse(a.pat)&&a.pc>=6){
      a.basis=MathAbs(a.pivots[5].price-a.pivots[0].price);
      if(a.basis<=0)return;
      a.tp1=org+d*a.basis*0.382;a.tp2=org+d*a.basis*0.618;a.tp3=org+d*a.basis;
   }else if(IsCorrection(a.pat)||IsCombination(a.pat)||a.pat==P_FAILED_5){
      if(a.pc<4)return;
      a.basis=MathAbs(a.pivots[3].price-a.pivots[2].price);
      if(a.basis<=0)a.basis=MathMax(a.atr,_Point*10);
      a.tp1=org+d*a.basis*0.618;a.tp2=org+d*a.basis;a.tp3=org+d*a.basis*1.618;
   }else if(IsTriangle(a.pat)){
      a.basis=hi-lo;if(a.basis<=0)return;
      a.tp1=org+d*a.basis*0.618;a.tp2=org+d*a.basis;a.tp3=org+d*a.basis*1.618;
   }else return;
   a.inval=(d>0)?lo-pad:hi+pad;
   a.tradeSL=a.inval;
   if(InpUseATRTradeStop){
      double stop=org-d*MathMax(a.atr*InpTradeStopATR,_Point*12.0);
      a.tradeSL=d>0?MathMax(a.inval,stop):MathMin(a.inval,stop);
   }
   a.tp1=NormalizeDouble(a.tp1,_Digits);a.tp2=NormalizeDouble(a.tp2,_Digits);
   a.tp3=NormalizeDouble(a.tp3,_Digits);a.inval=NormalizeDouble(a.inval,_Digits);
   a.tradeSL=NormalizeDouble(a.tradeSL,_Digits);
}
void ResetTree(){g_treeCount=0;g_nextNodeId=1;}
long TreeCreate(const WaveNode &n){
   if(g_treeCount>=MAX_NODES)return -1;
   long id=g_nextNodeId++;
   g_tree[g_treeCount]=n;g_tree[g_treeCount].id=id;
   g_tree[g_treeCount].childCount=0;
   g_tree[g_treeCount].parent=n.parent;
   for(int i=0;i<MAX_LEGS;i++)g_tree[g_treeCount].children[i]=0;
   g_treeCount++;return id;
}
int TreeFind(long id){
   static long lid=-1;static int lix=-1;
   if(id==lid&&lix>=0&&lix<g_treeCount&&g_tree[lix].id==id)return lix;
   for(int i=0;i<g_treeCount;i++)if(g_tree[i].id==id){lid=id;lix=i;return i;}
   return -1;
}
void TreeAddChild(long pid,long cid){
   int pi=TreeFind(pid);
   if(pi<0||g_tree[pi].childCount>=MAX_LEGS)return;
   g_tree[pi].children[g_tree[pi].childCount]=cid;
   g_tree[pi].childCount++;
   int ci=TreeFind(cid);if(ci>=0)g_tree[ci].parent=pid;
}
double StructuralFit(const Analy &P,const Analy &C){
   if(!P.avail||!C.avail)return 40.0;
   if(P.pc<2||C.pc<2)return 40.0;
   double score=50.0;
   datetime pS=P.pivots[0].time,pE=P.pivots[P.pc-1].time;
   datetime cS=C.pivots[0].time,cE=C.pivots[C.pc-1].time;
   if(cS>=pS&&cE<=pE)score+=15.0;else return 0.0;
   double pLo=P.pivots[0].price,pHi=P.pivots[0].price;
   for(int i=1;i<P.pc;i++){if(P.pivots[i].price<pLo)pLo=P.pivots[i].price;if(P.pivots[i].price>pHi)pHi=P.pivots[i].price;}
   double cLo=C.pivots[0].price,cHi=C.pivots[0].price;
   for(int i=1;i<C.pc;i++){if(C.pivots[i].price<cLo)cLo=C.pivots[i].price;if(C.pivots[i].price>cHi)cHi=C.pivots[i].price;}
   double tol=MathMax((pHi-pLo)*0.02,_Point*2.0);
   if(cLo>=pLo-tol&&cHi<=pHi+tol)score+=15.0;else return 0.0;
   int ld=Sgn(P.pivots[P.pc-1].price-P.pivots[P.pc-2].price);
   if(C.dir==ld)score+=20.0;else if(C.dir==-ld)score-=5.0;
   if(IsMotive(P.pat)&&IsMotive(C.pat))score+=10.0;
   else if(IsCorrection(P.pat)&&IsCorrection(C.pat))score+=10.0;
   return Clamp(score,0,100);
}
double ValidateDeepHierarchy(int pIdx,int cIdx){
   if(pIdx<0||pIdx>=g_tfCount)return 40.0;
   if(cIdx<0||cIdx>=g_tfCount)return 40.0;
   if(!g_mtf[pIdx].avail||!g_mtf[cIdx].avail)return 40.0;
   Analy P=g_mtf[pIdx],C=g_mtf[cIdx];
   double score=50.0;
   datetime pS=P.pivots[0].time,pE=P.pivots[P.pc-1].time;
   datetime cS=C.pivots[0].time,cE=C.pivots[C.pc-1].time;
   if(cS>=pS&&cE<=pE)score+=12.0;else return 0.0;
   double pLo=P.pivots[0].price,pHi=P.pivots[0].price;
   for(int i=1;i<P.pc;i++){if(P.pivots[i].price<pLo)pLo=P.pivots[i].price;if(P.pivots[i].price>pHi)pHi=P.pivots[i].price;}
   double cLo=C.pivots[0].price,cHi=C.pivots[0].price;
   for(int i=1;i<C.pc;i++){if(C.pivots[i].price<cLo)cLo=C.pivots[i].price;if(C.pivots[i].price>cHi)cHi=C.pivots[i].price;}
   double pR=pHi-pLo;
   if(pR>0){double cL2=(cLo-pLo)/pR,cH2=(cHi-pLo)/pR;if(cL2>=-0.02&&cH2<=1.02)score+=12.0;else return 0.0;}
   if(IsMotive(P.pat)){
      int li=-1;
      for(int i=1;i<P.pc;i++)if(C.pivots[0].time>=P.pivots[i-1].time&&C.pivots[C.pc-1].time<=P.pivots[i].time){li=i-1;break;}
      if(li>=0){
         bool isM=(li%2==0);
         if(isM){if(IsMotive(C.pat))score+=15.0;else if(IsCorrection(C.pat))score-=8.0;}
         else{if(IsCorrection(C.pat)||IsTriangle(C.pat))score+=15.0;else if(IsMotive(C.pat))score-=8.0;}
         int pD=Sgn(P.pivots[li+1].price-P.pivots[li].price);
         if(C.dir==pD)score+=10.0;else if(C.dir!=0)score-=5.0;
      }
   }
   if(IsMotive(P.pat)&&P.pc>=6)score+=5.0;
   return Clamp(score,0,100);
}
void BuildWaveTree(){
   ResetTree();
   for(int i=0;i<MAX_TF;i++)g_tfNodeIdx[i]=-1;
   if(!InpUseHierarchy)return;
   for(int i=g_tfCount-1;i>=0;i--){
      if(!g_mtf[i].avail)continue;
      WaveNode nd;
      nd.id=0;nd.parent=-1;nd.childCount=0;
      for(int k=0;k<MAX_LEGS;k++)nd.children[k]=0;
      nd.tf=g_mtf[i].tf;nd.pattern=g_mtf[i].pat;nd.dir=g_mtf[i].dir;
      nd.compositeScore=g_mtf[i].composite;
      nd.align=A_NONE;nd.alignScore=0;nd.fitsInParent=false;nd.structuralFit=40;
      long pid=-1;
      for(int j=i+1;j<g_tfCount;j++){if(g_tfNodeIdx[j]>=0){pid=g_tree[g_tfNodeIdx[j]].id;break;}}
      nd.parent=pid;
      long nid=TreeCreate(nd);
      if(nid<0)continue;
      g_tfNodeIdx[i]=g_treeCount-1;
      if(pid>=0){
         TreeAddChild(pid,nid);
         int pi=TreeFind(pid);
         if(pi>=0){
            int pTI=TFIdx(g_tree[pi].tf);
            if(pTI>=0){
               double fs=StructuralFit(g_mtf[pTI],g_mtf[i]);
               double fd=ValidateDeepHierarchy(pTI,i);
               double fit=fs*0.40+fd*0.60;
               int ni=g_tfNodeIdx[i];
               if(ni>=0){g_tree[ni].structuralFit=fit;g_tree[ni].fitsInParent=(fit>=g_activeHierMin);}
            }
         }
      }
   }
   for(int i=0;i<g_tfCount;i++){
      if(!g_mtf[i].avail||g_tfNodeIdx[i]<0){g_mtf[i].hierConf=40.0;g_mtf[i].deepHier=0;continue;}
      int ni=g_tfNodeIdx[i];
      double fit=g_tree[ni].structuralFit;
      double pc=40.0;
      if(g_tree[ni].parent>=0){
         int pi=TreeFind(g_tree[ni].parent);
         if(pi>=0){int pTI=TFIdx(g_tree[pi].tf);if(pTI>=0)pc=g_mtf[pTI].composite;}
      }
      g_mtf[i].hierConf=Clamp(fit*0.60+pc*0.40,0,100);
      g_mtf[i].deepHier=fit;
   }
}
void ComputeConsensus(){
   g_cons.dominantDir=0;g_cons.weightedAgree=0;
   g_cons.confirmCount=0;g_cons.divergeCount=0;g_cons.neutralCount=0;
   g_cons.domTF=g_curTF;g_cons.domStrength=0;
   g_cons.tradeReady=false;g_cons.overallAlign=A_GRAY;
   double up=0,dn=0,total=0;
   for(int i=0;i<g_tfCount;i++){
      g_mtf[i].align=A_GRAY;g_mtf[i].alignScore=0;
      if(!g_mtf[i].avail)continue;
      total+=TFWeight(i);
      bool hOK=!InpUseHierarchy||g_mtf[i].hierConf>=g_activeHierMin;
      bool elig=g_mtf[i].active&&g_mtf[i].qualified&&hOK;
      if(!elig||g_mtf[i].futDir==0){g_cons.neutralCount++;continue;}
      double v=TFWeight(i)*g_mtf[i].quality/100.0;
      if(g_mtf[i].futDir>0)up+=v;else dn+=v;
      if(v>g_cons.domStrength){g_cons.domStrength=v;g_cons.domTF=g_mtf[i].tf;}
   }
   if(up>dn)g_cons.dominantDir=1;
   else if(dn>up)g_cons.dominantDir=-1;
   double ag=0;
   for(int i=0;i<g_tfCount;i++){
      if(!g_mtf[i].avail||!g_mtf[i].active||!g_mtf[i].qualified)continue;
      if(InpUseHierarchy&&g_mtf[i].hierConf<g_activeHierMin)continue;
      if(g_mtf[i].futDir==0)continue;
      if(g_cons.dominantDir==0){g_mtf[i].align=A_GOLD;continue;}
      if(g_mtf[i].futDir==g_cons.dominantDir){
         g_cons.confirmCount++;ag+=TFWeight(i);
         g_mtf[i].align=A_GOLD;g_mtf[i].alignScore=75;
      }else{g_cons.divergeCount++;g_mtf[i].align=A_RED;}
   }
   if(total>0)g_cons.weightedAgree=100.0*ag/total;
   if(g_cons.dominantDir==0){if(up>0&&dn>0)g_cons.overallAlign=A_RED;return;}
   if(g_cons.weightedAgree>=70&&g_cons.confirmCount>=3)g_cons.overallAlign=A_GREEN;
   else if(g_cons.weightedAgree>=55)g_cons.overallAlign=A_GOLD;
   else if(g_cons.divergeCount>=g_cons.confirmCount)g_cons.overallAlign=A_RED;
   int ci=TFIdx(g_curTF);
   g_cons.tradeReady=g_cons.overallAlign==A_GREEN&&ci>=0&&
      g_mtf[ci].active&&g_mtf[ci].qualified&&
      g_mtf[ci].align==A_GOLD&&g_mtf[ci].futDir==g_cons.dominantDir;
   if(g_cons.tradeReady)g_mtf[ci].align=A_GREEN;
}
bool IsTradingSession(datetime t){
   if(!InpFilterSessions)return true;
   MqlDateTime dt;TimeToStruct(t,dt);
   int h=dt.hour;
   if(h>=23||h<7)return false;
   if(h==22)return false;
   return true;
}
bool SpreadOK(){
   if(InpMinSpreadPoints<=0)return true;
   long sp=SymbolInfoInteger(_Symbol,SYMBOL_SPREAD);
   return(sp<=InpMinSpreadPoints);
}
int GetHTFBias(){
   if(!InpHTFBiasFilter)return 0;
   ENUM_TIMEFRAMES htf=(ENUM_TIMEFRAMES)InpHTFBiasTF;
   MqlRates r[];int cnt=CopyRates(_Symbol,htf,1,60,r);
   if(cnt<60)return 0;
   ArraySetAsSeries(r,false);
   double a20=2.0/21.0,a50=2.0/51.0;
   double e20=r[0].close,e50=r[0].close;
   for(int i=1;i<cnt;i++){e20=a20*r[i].close+(1.0-a20)*e20;e50=a50*r[i].close+(1.0-a50)*e50;}
   double c=r[cnt-1].close;
   if(c>e20&&e20>e50)return 1;
   if(c<e20&&e20<e50)return -1;
   return 0;
}
bool IsNewsBlackout(datetime t){
   if(InpNewsBlackoutMin<=0)return false;
   MqlDateTime dt;TimeToStruct(t,dt);
   if(dt.day_of_week==0||dt.day_of_week==6)return false;
   if(dt.day_of_week==5&&dt.hour>=21)return false;
   if(dt.day_of_week==1&&dt.hour<2)return false;
   int hs[]={13,15,18,21};int ms[]={30,0,0,0};
   int currentMin=dt.hour*60+dt.min;
   for(int i=0;i<4;i++){
      int newsMin=hs[i]*60+ms[i];
      if(MathAbs(currentMin-newsMin)<=InpNewsBlackoutMin)return true;
   }
   return false;
}
bool ValidateScenario(Analy &out,const MqlRates &rates[],int cnt){
   if(!IsTradingSession(TimeCurrent())){out.state="OFF SESSION";return true;}
   if(!SpreadOK()){out.state="SPREAD WIDE";return true;}
   if(IsNewsBlackout(TimeCurrent())){out.state="NEWS BLACKOUT";return true;}
   if(InpHTFBiasFilter&&out.futDir!=0){
      int hb=GetHTFBias();
      if(hb!=0&&hb!=out.futDir){out.state="HTF CONFLICT";return true;}
   }
   out.active=false;out.qualified=false;out.structureValid=false;
   int ready=out.readyBar,d=out.futDir;
   if(ready<0||ready>=cnt||d==0||out.basis<=0){out.state="NO SETUP";return true;}
   double rw=d*(out.tp1-out.entry);
   double rk=d*(out.entry-out.tradeSL);
   if(rw<=_Point||rk<=_Point||d*(out.entry-out.inval)<=_Point){out.state="INVALID LEVELS";return true;}
   out.structureValid=out.hardRules;
   string oc="";
   for(int b=ready+1;b<cnt;b++){
      bool inv=d>0?rates[b].low<=out.inval:rates[b].high>=out.inval;
      bool st=d>0?rates[b].low<=out.tradeSL:rates[b].high>=out.tradeSL;
      bool hi=d>0?rates[b].high>=out.tp1:rates[b].low<=out.tp1;
      if(inv)out.structureValid=false;
      if(oc==""){if(st)oc="STOP HIT";else if(hi)oc="TP1 REACHED";}
   }
   if(!out.structureValid){out.state="INVALIDATED";return true;}
   if(oc!=""){out.state=oc;return true;}
   if(cnt-1-ready>InpHorizonBars){out.state="EXPIRED";return true;}
   out.active=true;
   bool subOK=!InpRequireSubwaves||out.sSub>=g_activeMinSub;
   out.qualified=out.hardRules&&out.quality>=g_activeMinScore&&subOK&&rw/rk>=g_activeMinRR&&cnt-1-ready<=InpMaxEntryAgeBars;
   if(out.qualified)out.state="CONFIRMED";
   else if(cnt-1-ready>InpMaxEntryAgeBars)out.state="ENTRY STALE";
   else if(!subOK)out.state=out.sSub<0?"SUB DATA MISSING":"SUB UNVERIFIED";
   else if(rw/rk<g_activeMinRR)out.state="LOW R/R";
   else out.state="LOW SCORE";
   return true;
}
bool AnalyzeTF(ENUM_TIMEFRAMES tf,int histBars,int maxPiv,Analy &out,Pivot &outPiv[],bool storeCache){
   ResetAnaly(out,tf);ArrayResize(outPiv,0);
   MqlRates rates[];double atr[];int cnt=0;
   if(!LoadRates(tf,histBars,rates,cnt)||!BuildATR(rates,cnt,atr))return false;
   if(!BuildAdaptivePivots(rates,atr,cnt,maxPiv,outPiv))return false;
   int total=ArraySize(outPiv);
   if(storeCache||tf==GetChartTF())PrepareCorrCache(outPiv,total,tf);
   if(storeCache){
      int idx=TFIdx(tf);
      if(idx>=0){
         int mc=MathMin(total,MAX_CACHE);
         ArrayResize(g_cache[idx].pivots,mc);
         for(int i=0;i<mc;i++)g_cache[idx].pivots[i]=outPiv[i];
         g_cache[idx].count=mc;g_cache[idx].atr=atr[cnt-1];
         g_cache[idx].ready=true;g_cache[idx].stamp=TimeLocal();
      }
   }
   Scenario sc[MAX_SCENARIOS];int scnC=0;
   int lens[3]={6,5,4};
   for(int i=0;i<3;i++){
      int n=lens[i];if(total<n)continue;
      Candidate c;
      if(!BestCand(outPiv,total,total-n,n,c))continue;
      RunScoring(c,outPiv,tf);
      if(scnC<MAX_SCENARIOS){sc[scnC].cand=c;sc[scnC].score=c.composite;sc[scnC].label=TFName(tf);scnC++;}
   }
   for(int i=0;i<scnC-1;i++)
      for(int j=0;j<scnC-1-i;j++)
         if(sc[j].score<sc[j+1].score){Scenario t=sc[j];sc[j]=sc[j+1];sc[j+1]=t;}
   Candidate prim;ResetCand(prim);
   if(scnC>0)prim=sc[0].cand;
   if(!prim.valid||prim.composite<InpMinScore){
      MakeSwing(outPiv,MathMax(0,total-6),total-1,prim);
      RunScoring(prim,outPiv,tf);
   }
   if(prim.s<0||prim.s>=total||prim.n<2||prim.s+prim.n>total){ResetAnaly(out,tf);return false;}
   out.avail=true;out.pat=prim.pat;out.dir=prim.dir;out.preDir=prim.preDir;
   if(InpCheckDiagPosition&&IsDiagonal(prim.pat)){
      EPAT dp=DetectDiagonalPosition(outPiv,prim,tf);
      if(dp!=P_DIAG_GENERIC)out.pat=dp;
   }
   out.futDir=FutureDir(prim.pat,prim.dir,prim.preDir);
   out.trunc=prim.trunc;out.ext=prim.ext;out.extW=prim.extW;
   out.pc=MathMin(prim.n,MAX_PTS);
   if(out.pc<2||prim.s+out.pc>total){ResetAnaly(out,tf);return false;}
   for(int i=0;i<out.pc;i++)out.pivots[i]=outPiv[prim.s+i];
   out.prov=false;
   out.sStruct=prim.sStruct;out.sSub=prim.sSub;out.sFib=prim.sFib;
   out.sAlt=prim.sAlt;out.sChan=prim.sChan;out.sPers=prim.sPers;out.sTime=prim.sTime;
   out.sVol=prim.sVol;out.sDegree=prim.sDegree;out.sInner=prim.sInner;
   out.sMomentum=prim.sMomentum;
   out.composite=prim.composite;out.hardRules=prim.hardRules;
   out.sAlt2=prim.sAlt2;
   out.channelOK=prim.channelOK;out.channelErr=prim.channelErr;
   out.volumeOK=prim.volumeOK;out.alternationOK=prim.alternationOK;
   out.degreeOK=prim.degreeOK;out.innerOK=prim.innerOK;
   out.fibClusterScore=prim.fibClusterScore;
   out.isCombination=(prim.pat==P_WXY||prim.pat==P_WXYXZ||prim.pat==P_DIAMOND||prim.pat==P_TRI_RUN||prim.pat==P_FAILED_5);
   out.comboLegs=prim.legs;
   out.failedPct=prim.failedPct;out.isRunning=prim.isRunning;
   out.isDiamond=prim.isDiamond;out.patternQuality=prim.patternQuality;
   int ready=out.pivots[out.pc-1].confirmedBar+InpConfirmDelay;
   out.readyBar=ready;
   out.atr=atr[(int)MathMin(cnt-1,MathMax(0,ready))];
   int ci=TFIdx(tf);
   double ctx=CtxScoreFast(ci,out.futDir,rates[cnt-1].close);
   out.quality=Clamp(prim.composite*0.85+ctx*0.15,0,100);
   out.state="NO SETUP";
   if(out.futDir==0)return true;
   if(ready>=cnt){out.state="CONFIRMING";return true;}
   out.readyTime=rates[ready].time;
   out.entry=rates[ready].close;
   ComputeTargets(out);
   return ValidateScenario(out,rates,cnt);
}
void AnalyzeDashboard(){
   for(int i=0;i<g_tfCount;i++){
      g_cache[i].ready=false;g_cache[i].count=0;
      MqlRates rates[];double atr[];Pivot pv[];int cnt=0;
      if(!LoadRates(g_tfList[i],InpMTFBars,rates,cnt))continue;
      if(!BuildATR(rates,cnt,atr))continue;
      if(!BuildPivots(rates,atr,cnt,g_activePivotMult,pv))continue;
      int n=ArraySize(pv);int keep=MathMin(n,MAX_CACHE);
      ArrayResize(g_cache[i].pivots,keep);
      for(int j=0;j<keep;j++)g_cache[i].pivots[j]=pv[n-keep+j];
      g_cache[i].count=keep;g_cache[i].ready=true;
      g_cache[i].atr=atr[cnt-1];g_cache[i].stamp=TimeCurrent();
      PrepareEMACache(g_tfList[i],i);
   }
   for(int i=0;i<g_tfCount;i++){
      Analy a;Pivot pv[];
      if(AnalyzeTF(g_tfList[i],InpMTFBars,InpMaxMTFPivots,a,pv,false))g_mtf[i]=a;
      else ResetAnaly(g_mtf[i],g_tfList[i]);
      g_seenClosed[i]=iTime(_Symbol,g_tfList[i],1);
   }
   if(InpUseHierarchy)BuildWaveTree();
   ComputeConsensus();
   g_lastRefresh=TimeLocal();
}
// v14.4 OPTIMIZED: Chunked growth for g_chartMap
bool AnalyzeCurrentChart(){
   g_curTF=GetChartTF();
   Pivot pv[];Analy a;
   if(!AnalyzeTF(g_curTF,InpChartBars,InpMaxChartPivots,a,pv,false)){
      ResetAnaly(g_chart,g_curTF);
      ArrayResize(g_chartPiv,0);ArrayResize(g_chartMap,0);
      g_chartReady=false;return false;
   }
   int ci=TFIdx(g_curTF);
   if(ci>=0&&g_mtf[ci].avail)g_chart=g_mtf[ci];else g_chart=a;
   int pc=ArraySize(pv);
   ArrayResize(g_chartPiv,pc);
   for(int i=0;i<pc;i++)g_chartPiv[i]=pv[i];
   ArrayResize(g_chartMap,0);
   PrepareCorrCache(pv,pc,g_curTF);
   if(pc>0)ComputeAltRun(g_chartPiv,pc);
   if(pc<4){g_chartReady=true;return true;}
   int step=InpScanStep;
   if(InpAutoScanStep){int as=(pc>8000)?4:(pc>4000)?3:(pc>1500)?2:1;if(as>step)step=as;}
   if(step<1)step=1;
   int s=0;int maxD=MathMax(1,InpMaxWavesDrawn);
   int cap=CHUNK_INIT;
   ArrayResize(g_chartMap,cap);
   int mapN=0;
   while(s<pc-3&&mapN<maxD){
      if(s>=ArraySize(g_altRun)||g_altRun[s]<4){
         if(InpShowGapFillers){
            int ne=MathMin(s+4,pc-1);
            Candidate sw;MakeSwing(g_chartPiv,s,ne,sw);
            sw.sStruct=22.0;sw.composite=22.0;sw.hardRules=false;
            if(mapN>=cap){cap=cap+MathMax(CHUNK_MIN,cap/2);ArrayResize(g_chartMap,cap);}
            g_chartMap[mapN++]=sw;
         }
         s+=step;continue;
      }
      Candidate best;ResetCand(best);
      if(s+5<pc){Candidate c6;if(BestCand(g_chartPiv,pc,s,6,c6)){RunScoring(c6,g_chartPiv,g_curTF);if(c6.hardRules&&c6.composite>=InpMinPatternScore)best=c6;}}
      if(s+4<pc){Candidate c5;if(BestCand(g_chartPiv,pc,s,5,c5)){RunScoring(c5,g_chartPiv,g_curTF);if(c5.hardRules&&c5.composite>=InpMinPatternScore&&(!best.valid||c5.composite>best.composite))best=c5;}}
      if(s+3<pc){Candidate c4;if(BestCand(g_chartPiv,pc,s,4,c4)){RunScoring(c4,g_chartPiv,g_curTF);if(c4.hardRules&&c4.composite>=InpMinPatternScore&&(!best.valid||c4.composite>best.composite))best=c4;}}
      if(best.valid){
         if(mapN>=cap){cap=cap+MathMax(CHUNK_MIN,cap/2);ArrayResize(g_chartMap,cap);}
         g_chartMap[mapN++]=best;
         s=best.e+1;
      }else{
         if(InpShowGapFillers){
            int ne=MathMin(s+4,pc-1);
            Candidate sw;MakeSwing(g_chartPiv,s,ne,sw);
            sw.sStruct=22.0;sw.composite=22.0;sw.hardRules=false;
            if(mapN>=cap){cap=cap+MathMax(CHUNK_MIN,cap/2);ArrayResize(g_chartMap,cap);}
            g_chartMap[mapN++]=sw;
         }
         s+=step;
      }
   }
   if(mapN<ArraySize(g_chartMap))ArrayResize(g_chartMap,mapN);
   g_chartReady=true;return true;
}
void ClearObjects(){int t=ObjectsTotal(0,-1,-1);for(int i=t-1;i>=0;i--){string nm=ObjectName(0,i,-1,-1);if(StringFind(nm,g_pfx)==0)ObjectDelete(0,nm);}}
void PruneFamily(string fp,int kb){
   int t=ObjectsTotal(0,-1,-1);
   string full=g_pfx+fp;int pl=StringLen(full);
   for(int i=t-1;i>=0;i--){
      string nm=ObjectName(0,i,-1,-1);
      if(StringFind(nm,full)!=0)continue;
      string sfx=StringSubstr(nm,pl);
      int idx=0;bool isn=false;
      for(int c=0;c<StringLen(sfx);c++){ushort ch=StringGetCharacter(sfx,c);if(ch>='0'&&ch<='9'){idx=idx*10+(ch-'0');isn=true;}else break;}
      if(isn&&idx>=kb)ObjectDelete(0,nm);
   }
}
void PruneAllFamilies(){
   PruneFamily("SK_",g_hiSK);PruneFamily("H_",g_hiHist);
   PruneFamily("HL_",g_hiHL);PruneFamily("C_",g_hiCur);
   PruneFamily("CL_",g_hiCL);PruneFamily("SIG_L",g_hiSigL);
}
void ResetAllCounters(){g_hiSK=0;g_hiHist=0;g_hiHL=0;g_hiCur=0;g_hiCL=0;g_hiSigL=0;g_hiLink=0;}
void Line(string nm,datetime t1,double p1,datetime t2,double p2,color clr,int w,ENUM_LINE_STYLE st,bool ray,bool back){
   if(ObjectFind(0,nm)<0){
      if(!ObjectCreate(0,nm,OBJ_TREND,0,t1,p1,t2,p2))return;
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
   }else{ObjectMove(0,nm,0,t1,p1);ObjectMove(0,nm,1,t2,p2);}
   ObjectSetInteger(0,nm,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,nm,OBJPROP_WIDTH,w);
   ObjectSetInteger(0,nm,OBJPROP_STYLE,st);
   ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,ray);
   ObjectSetInteger(0,nm,OBJPROP_BACK,back);
}
void TextEx(string nm,datetime t,double p,string txt,color clr,int fs,ENUM_ANCHOR_POINT anc){
   if(ObjectFind(0,nm)<0){
      if(!ObjectCreate(0,nm,OBJ_TEXT,0,t,p))return;
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
      ObjectSetInteger(0,nm,OBJPROP_ZORDER,100);
   }else ObjectMove(0,nm,0,t,p);
   ObjectSetString(0,nm,OBJPROP_TEXT,txt);
   ObjectSetString(0,nm,OBJPROP_FONT,CurFont());
   ObjectSetInteger(0,nm,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,fs);
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,anc);
}
void Text(string nm,datetime t,double p,string txt,color clr,int fs){TextEx(nm,t,p,txt,clr,fs,ANCHOR_CENTER);}
void SLbl(string nm,int x,int y,color clr,int fs,string txt){
   if(ObjectFind(0,nm)<0){
      if(!ObjectCreate(0,nm,OBJ_LABEL,0,0,0))return;
      ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,true);
      ObjectSetInteger(0,nm,OBJPROP_ZORDER,50);
   }
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,fs);
   ObjectSetString(0,nm,OBJPROP_FONT,CurFont());
   ObjectSetInteger(0,nm,OBJPROP_ANCHOR,ANCHOR_LEFT_UPPER);
   ObjectSetString(0,nm,OBJPROP_TEXT,txt);
}
void BtnV14(string nm,string txt,int x,int y,int w,int h,color clr){
   if(ObjectFind(0,nm)<0){
      if(!ObjectCreate(0,nm,OBJ_BUTTON,0,0,0))return;
      ObjectSetInteger(0,nm,OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,nm,OBJPROP_BORDER_COLOR,C'60,80,110');
      ObjectSetInteger(0,nm,OBJPROP_FONTSIZE,9);
      ObjectSetInteger(0,nm,OBJPROP_ZORDER,2000);
      ObjectSetInteger(0,nm,OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,nm,OBJPROP_HIDDEN,false);
      ObjectSetInteger(0,nm,OBJPROP_STATE,false);
   }
   ObjectSetInteger(0,nm,OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,nm,OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,nm,OBJPROP_XSIZE,w);
   ObjectSetInteger(0,nm,OBJPROP_YSIZE,h);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,nm,OBJPROP_BGCOLOR,C'17,26,42');
   ObjectSetString(0,nm,OBJPROP_FONT,"Consolas");
   ObjectSetString(0,nm,OBJPROP_TEXT,txt);
   ObjectSetInteger(0,nm,OBJPROP_STATE,false);
}
color HistColor(EPAT p){
   if(IsImpulse(p))return ClrHistImpulse;
   if(IsDiagonal(p))return ClrDiagonal;
   if(p==P_DIAMOND)return ClrDiamond;
   if(p==P_TRI_RUN)return ClrRunTri;
   if(p==P_FAILED_5)return ClrFailed5;
   if(p==P_ZIGZAG||IsFlat(p)||IsCombination(p))return ClrHistCorrection;
   if(IsTriangle(p))return ClrTriangle;
   return ClrSkeleton;
}
color CurColor(EPAT p){
   if(IsImpulse(p))return ClrImpulse;
   if(IsDiagonal(p))return ClrDiagonal;
   if(p==P_DIAMOND)return ClrDiamond;
   if(p==P_TRI_RUN)return ClrRunTri;
   if(p==P_FAILED_5)return ClrFailed5;
   if(p==P_ZIGZAG||IsFlat(p)||IsCombination(p))return ClrCorrection;
   if(IsTriangle(p))return ClrTriangle;
   return ClrCurrent;
}
string WaveLbl(EPAT p,int i,bool trunc){
   string b="";
   if(IsMotive(p)){string L[6]={"0","1","2","3","4","5"};if(i>=0&&i<6){if(trunc&&i==5)b="5*";else b=L[i];}}
   else if(p==P_FAILED_5){string L[6]={"0","1","2","3","4","5F"};if(i>=0&&i<6)b=L[i];}
   else if(p==P_DIAMOND){string L[6]={"D0","D1","D2","D3","D4","D5"};if(i>=0&&i<6)b=L[i];}
   else if(p==P_TRI_RUN){string L[5]={"A","B","C","D","E"};if(i>=0&&i<5)b=L[i];}
   else if(p==P_WXY){string L[7]={"W0","W1","W2","X","Y0","Y1","Y2"};if(i>=0&&i<7)b=L[i];}
   else if(p==P_WXYXZ){string L[11]={"W0","W1","W2","X1","Y0","Y1","Y2","X2","Z0","Z1","Z2"};if(i>=0&&i<11)b=L[i];}
   else if(p==P_ZIGZAG||IsFlat(p)){string L[4]={"0","A","B","C"};if(i>=0&&i<4)b=L[i];}
   else if(IsTriangle(p)){string L[6]={"0","A","B","C","D","E"};if(i>=0&&i<6)b=L[i];}
   return b;
}
void DrawHistorical(){
   if(!InpShowHistory){g_hiSK=0;g_hiHist=0;g_hiHL=0;return;}
   int pc=ArraySize(g_chartPiv);
   if(pc<2){g_hiSK=0;g_hiHist=0;g_hiHL=0;return;}
   long sec=PeriodSeconds(g_curTF);if(sec<=0)sec=60;
   if(InpShowSkeleton){
      g_hiSK=pc-1;
      for(int i=1;i<pc;i++)
         Line(g_pfx+"SK_"+IntegerToString(i),
              g_chartPiv[i-1].time,g_chartPiv[i-1].price,
              g_chartPiv[i].time,g_chartPiv[i].price,
              ClrSkeleton,1,STYLE_DOT,false,true);
   }else g_hiSK=0;
   int mc=ArraySize(g_chartMap);
   g_hiHist=mc;g_hiHL=mc;
   for(int m=0;m<mc;m++){
      Candidate w=g_chartMap[m];
      if(!w.valid)continue;
      color clr=HistColor(w.pat);
      int ww=InpLineWidth;
      if(w.pat==P_SWING){clr=ClrSkeleton;ww=1;}
      for(int leg=1;leg<w.n;leg++){
         int l=w.s+leg-1,r=w.s+leg;
         if(l<0||r>=pc)continue;
         Line(g_pfx+"H_"+IntegerToString(m)+"_"+IntegerToString(leg),
              g_chartPiv[l].time,g_chartPiv[l].price,
              g_chartPiv[r].time,g_chartPiv[r].price,
              clr,ww,STYLE_SOLID,false,true);
      }
      if(InpShowHistoryLabels&&w.pat!=P_SWING){
         for(int q=0;q<w.n;q++){
            int idx=w.s+q;
            if(idx<0||idx>=pc)continue;
            string lb=WaveLbl(w.pat,q,w.trunc);
            if(lb=="")continue;
            double off=g_chart.atr*0.30;
            if(off<_Point*15.0)off=_Point*15.0;
            double lp=g_chartPiv[idx].price+(g_chartPiv[idx].isHigh?off:-off);
            datetime lt=g_chartPiv[idx].time+(datetime)(sec*0.5);
            Text(g_pfx+"HL_"+IntegerToString(m)+"_"+IntegerToString(q),lt,lp,lb,clr,7);
         }
      }
   }
}
void DrawCurrent(){
   if(!InpShowCurrent||!g_chart.avail){g_hiCur=0;g_hiCL=0;return;}
   if(g_chart.pc<2){g_hiCur=0;g_hiCL=0;return;}
   color clr=CurColor(g_chart.pat);
   long sec=PeriodSeconds(g_curTF);if(sec<=0)sec=60;
   g_hiCur=g_chart.pc-1;
   for(int i=1;i<g_chart.pc;i++){
      color lc=(i==g_chart.pc-1)?ClrCurrent:clr;
      int w=(i==g_chart.pc-1)?4:3;
      Line(g_pfx+"C_"+IntegerToString(i),
           g_chart.pivots[i-1].time,g_chart.pivots[i-1].price,
           g_chart.pivots[i].time,g_chart.pivots[i].price,
           lc,w,STYLE_SOLID,false,false);
   }
   if(!InpShowCurrentLabels){g_hiCL=0;return;}
   g_hiCL=g_chart.pc;
   int fs=(g_chart.composite>=60)?12:10;
   double off=MathMax(g_chart.atr*0.50,_Point*30.0);
   for(int i=0;i<g_chart.pc;i++){
      string lb=WaveLbl(g_chart.pat,i,g_chart.trunc);
      if(lb=="")continue;
      double lp=g_chart.pivots[i].price+(g_chart.pivots[i].isHigh?off:-off);
      datetime lt=g_chart.pivots[i].time+(datetime)(sec*0.5);
      color lc=(i==g_chart.pc-1)?ClrCurrent:clr;
      ENUM_ANCHOR_POINT anc=g_chart.pivots[i].isHigh?ANCHOR_LOWER:ANCHOR_UPPER;
      TextEx(g_pfx+"CL_"+IntegerToString(i),lt,lp,lb,lc,fs,anc);
   }
}
void EnsureFutureSpace(){
   if(!InpAutoShift)return;
   if(!ChartGetInteger(0,CHART_SHIFT))ChartSetInteger(0,CHART_SHIFT,true);
   double w=Clamp(InpShiftPercent,10,50);
   if(MathAbs(ChartGetDouble(0,CHART_SHIFT_SIZE)-w)>0.05)ChartSetDouble(0,CHART_SHIFT_SIZE,w);
}
int FutureBars(){
   long wb=ChartGetInteger(0,CHART_WIDTH_IN_BARS);
   if(wb<=0)return InpProjectionBars;
   double sh=Clamp(InpShiftPercent,10,50);
   int av=(int)MathFloor(wb*sh/100.0*0.75);
   if(av<12)av=12;
   int r=MathMin(InpProjectionBars,av);
   if(r<12)r=12;
   return r;
}
void DrawFuture(){
   if(!InpShowFuture||!g_chart.avail||!g_chart.active)return;
   if(g_chart.pc<2||g_chart.futDir==0)return;
   EnsureFutureSpace();
   long sec=PeriodSeconds(g_curTF);if(sec<=0)sec=60;
   int tot=FutureBars();
   int b1=MathMax(4,(int)MathRound(tot*0.34));
   int b2=MathMax(3,(int)MathRound(tot*0.22));
   int b3=MathMax(5,tot-b1-b2);
   Pivot org=g_chart.pivots[g_chart.pc-1];
   datetime ct=iTime(_Symbol,g_curTF,0);if(ct<=0)ct=TimeCurrent();
   datetime t1=ct+(datetime)(sec*b1);
   datetime t2=t1+(datetime)(sec*b2);
   datetime t3=t2+(datetime)(sec*b3);
   double p1=g_chart.tp1;
   double p2=p1-g_chart.futDir*g_chart.basis*0.30;
   double p3=g_chart.tp3;
   string l1="NEXT 1",l2="NEXT 2",l3="NEXT 3";
   if(IsMotive(g_chart.pat)){l1="A";l2="B";l3="C";p3=g_chart.tp2;}
   else if(IsCorrection(g_chart.pat)||IsCombination(g_chart.pat)){l1="(1)";l2="(2)";l3="(3)";}
   else if(IsTriangle(g_chart.pat)){l1="THRUST";l2="RETEST";l3="TARGET";p3=g_chart.tp2;}
   Line(g_pfx+"F1",org.time,org.price,t1,p1,ClrFuture,2,STYLE_DASH,false,false);
   Line(g_pfx+"F2",t1,p1,t2,p2,ClrFuture,2,STYLE_DASH,false,false);
   Line(g_pfx+"F3",t2,p2,t3,p3,ClrFuture,2,STYLE_DASH,false,false);
   double wO=MathMax(g_chart.atr*0.60,_Point*30.0);
   int d=g_chart.futDir;
   TextEx(g_pfx+"FL1",t1,p1+d*wO,l1,ClrFuture,9,d>0?ANCHOR_LOWER:ANCHOR_UPPER);
   TextEx(g_pfx+"FL2",t2,p2-d*wO,l2,ClrFuture,9,d>0?ANCHOR_UPPER:ANCHOR_LOWER);
   TextEx(g_pfx+"FL3",t3,p3+d*wO,l3,ClrFuture,9,d>0?ANCHOR_LOWER:ANCHOR_UPPER);
}
void DrawSignalBox(){
   if(!InpShowEntryLabel||!g_chart.avail||!g_chart.active)return;
   if(g_chart.pc<1||g_chart.futDir==0)return;
   long sec=PeriodSeconds(g_curTF);if(sec<=0)sec=60;
   datetime lastTime=iTime(_Symbol,g_curTF,0);if(lastTime<=0)lastTime=TimeCurrent();
   datetime lineEnd=lastTime+(datetime)(sec*12);
   Pivot org=g_chart.pivots[g_chart.pc-1];
   int d=g_chart.futDir;
   int dg=(int)SymbolInfoInteger(_Symbol,SYMBOL_DIGITS);
   ESIGMODE mode=SM_NOT_READY;
   if(g_cons.tradeReady&&g_chart.active&&g_chart.qualified)mode=SM_CONFIRMED;
   else if(g_chart.hardRules&&g_cons.overallAlign!=A_RED)mode=SM_WATCH;
   color cE,cS,cT1,cT2,cT3;string ew;int lw;
   if(mode==SM_CONFIRMED){
      cE=(d>0)?ClrBuyEntry:ClrSellEntry;cS=ClrSL;
      cT1=ClrTP1;cT2=ClrTP2;cT3=ClrTP3;
      ew=(d>0)?"ENTRY BUY":"ENTRY SELL";lw=2;
   }else if(mode==SM_WATCH){
      cE=C'255,215,0';cS=C'220,120,120';
      cT1=C'110,210,150';cT2=C'110,190,230';cT3=C'190,140,210';
      ew=(d>0)?"WATCH BUY":"WATCH SELL";lw=2;
   }else{
      cE=C'170,180,190';cS=C'170,120,120';
      cT1=C'130,160,140';cT2=C'130,150,170';cT3=C'160,140,170';
      ew="REFERENCE";lw=1;
   }
   Line(g_pfx+"ENTRY_LINE",g_chart.readyTime,g_chart.entry,lineEnd,g_chart.entry,cE,lw+1,STYLE_SOLID,false,false);
   double slP=(g_chart.tradeSL>0)?g_chart.tradeSL:g_chart.inval;
   if(slP>0)Line(g_pfx+"SL_LINE",org.time,slP,lineEnd,slP,cS,lw,STYLE_DASH,false,false);
   if(InpShowTP1&&g_chart.tp1>0)Line(g_pfx+"TP1_LINE",org.time,g_chart.tp1,lineEnd,g_chart.tp1,cT1,lw,STYLE_DASH,false,false);
   if(InpShowTP2&&g_chart.tp2>0)Line(g_pfx+"TP2_LINE",org.time,g_chart.tp2,lineEnd,g_chart.tp2,cT2,lw,STYLE_DASH,false,false);
   if(InpShowTP3&&g_chart.tp3>0)Line(g_pfx+"TP3_LINE",org.time,g_chart.tp3,lineEnd,g_chart.tp3,cT3,1,STYLE_DASH,false,false);
   SigItem items[6];int n=0;
   items[n].price=g_chart.entry;items[n].text=ew+"  "+DoubleToString(g_chart.entry,dg)+"      ";items[n].clr=cE;items[n].fs=10;n++;
   if(slP>0){items[n].price=slP;items[n].text="STOP LOSS  "+DoubleToString(slP,dg)+"      ";items[n].clr=cS;items[n].fs=9;n++;}
   if(InpShowTP1&&g_chart.tp1>0){items[n].price=g_chart.tp1;items[n].text="TAKE PROFIT 1  "+DoubleToString(g_chart.tp1,dg)+"      ";items[n].clr=cT1;items[n].fs=9;n++;}
   if(InpShowTP2&&g_chart.tp2>0){items[n].price=g_chart.tp2;items[n].text="TAKE PROFIT 2  "+DoubleToString(g_chart.tp2,dg)+"      ";items[n].clr=cT2;items[n].fs=9;n++;}
   if(InpShowTP3&&g_chart.tp3>0){items[n].price=g_chart.tp3;items[n].text="TAKE PROFIT 3  "+DoubleToString(g_chart.tp3,dg)+"      ";items[n].clr=cT3;items[n].fs=9;n++;}
   for(int i=0;i<n;i++)TextEx(g_pfx+"SIG_L"+IntegerToString(i),lineEnd,items[i].price,items[i].text,items[i].clr,items[i].fs,ANCHOR_RIGHT);
   for(int k=n;k<8;k++){string nm=g_pfx+"SIG_L"+IntegerToString(k);if(ObjectFind(0,nm)>=0)ObjectDelete(0,nm);}
   g_hiSigL=n;
}
double CalcMean(double &arr[]){int n=ArraySize(arr);if(n<=0)return 0;double s=0;for(int i=0;i<n;i++)s+=arr[i];return s/n;}
double CalcStdDev(double &arr[]){int n=ArraySize(arr);if(n<2)return 0;double m=CalcMean(arr),s=0;for(int i=0;i<n;i++)s+=(arr[i]-m)*(arr[i]-m);return MathSqrt(s/(n-1));}
double CalcSharpe(double &rr[],double rf=0){int n=ArraySize(rr);if(n<2)return 0;double m=CalcMean(rr),sd=CalcStdDev(rr);if(sd<=0)return 0;return(m-rf)/sd*MathSqrt(252.0);}
double CalcSortino(double &rr[],double tgt=0){
   int n=ArraySize(rr);if(n<2)return 0;
   double m=CalcMean(rr),dn=0;int cd=0;
   for(int i=0;i<n;i++)if(rr[i]<tgt){dn+=(rr[i]-tgt)*(rr[i]-tgt);cd++;}
   if(cd==0)return 999.0;
   double dd=MathSqrt(dn/cd);if(dd<=0)return 0;
   return(m-tgt)/dd*MathSqrt(252.0);
}
double CalcMaxDD(double &eq[]){
   int n=ArraySize(eq);if(n<2)return 0;
   double pk=eq[0],mx=0;
   for(int i=1;i<n;i++){if(eq[i]>pk)pk=eq[i];double dd=(pk-eq[i])/pk;if(dd>mx)mx=dd;}
   return mx*100.0;
}
BootstrapCI BootstrapWinRate(bool &wins[],int runs=1000){
   BootstrapCI ci;ci.lower=0;ci.upper=0;ci.mean=0;
   int n=ArraySize(wins);if(n<10)return ci;
   double rs[];ArrayResize(rs,runs);MathSrand(42);
   for(int r=0;r<runs;r++){int w=0;for(int i=0;i<n;i++){int idx=(int)(MathRand()%(uint)n);if(wins[idx])w++;}rs[r]=(double)w/n*100.0;}
   ArraySort(rs);
   ci.lower=rs[(int)(runs*0.025)];ci.upper=rs[(int)(runs*0.975)];ci.mean=CalcMean(rs);
   return ci;
}
MonteCarloResult RunMonteCarlo(double wr,double aw,double al,int runs){
   MonteCarloResult mc;mc.avgFinal=0;mc.worstCase=0;mc.bestCase=0;mc.avgDD=0;
   if(runs<10)return mc;
   MathSrand(123);
   double fin[];ArrayResize(fin,runs);double td=0;
   for(int r=0;r<runs;r++){
      double eq=1000.0,pk=1000.0,mx=0;
      for(int t=0;t<100;t++){double rn=(double)MathRand()/32767.0;if(rn<wr)eq+=aw;else eq-=al;if(eq>pk)pk=eq;double dd=(pk-eq)/pk;if(dd>mx)mx=dd;}
      fin[r]=eq;td+=mx;
   }
   ArraySort(fin);
   mc.avgFinal=CalcMean(fin);mc.worstCase=fin[0];mc.bestCase=fin[runs-1];mc.avgDD=td/runs*100.0;
   return mc;
}
void EnsureLogHeader(){
   if(!InpLogSignals)return;
   int h=FileOpen(g_logFileName,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0){FileWrite(h,"Ver","Time","Symbol","TF","Pattern","Dir","Entry","SL","TP1","TP2","TP3","Composite","Quality","Hier","ChanOK","VolOK","AltOK","DegOK","InnerOK","Mom","State","Outcome","R");FileFlush(h);}
   FileClose(h);
}
void LogSignal(const Analy &a){
   if(!InpLogSignals||!a.avail)return;
   int h=FileOpen(g_logFileName,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_COMMON,',');
   if(h==INVALID_HANDLE)return;
   if(FileSize(h)==0)FileWrite(h,"Ver","Time","Symbol","TF","Pattern","Dir","Entry","SL","TP1","TP2","TP3","Composite","Quality","Hier","ChanOK","VolOK","AltOK","DegOK","InnerOK","Mom","State","Outcome","R");
   FileSeek(h,0,SEEK_END);
   double oc=0;string res="OPEN";
   if(a.state=="TP1 REACHED"){oc=1.0;res="WIN";}
   else if(a.state=="STOP HIT"){oc=-1.0;res="LOSS";}
   else if(a.state=="INVALIDATED"){oc=-1.0;res="INVALID";}
   else if(a.state=="EXPIRED"){oc=0.0;res="FLAT";}
   else if(a.state=="CONFIRMED"){oc=0.0;res="PENDING";}
   double rm=0;
   if(oc!=0){double rk=MathAbs(a.entry-a.tradeSL),rw=MathAbs(a.tp1-a.entry);if(rk>_Point)rm=oc*(rw/rk);}
   FileWrite(h,EWQ_VER,TimeToString(a.readyTime,TIME_DATE|TIME_MINUTES),_Symbol,TFName(a.tf),
      PatName(a.pat),a.futDir,DoubleToString(a.entry,_Digits),DoubleToString(a.tradeSL,_Digits),
      DoubleToString(a.tp1,_Digits),DoubleToString(a.tp2,_Digits),DoubleToString(a.tp3,_Digits),
      DoubleToString(a.composite,1),DoubleToString(a.quality,1),DoubleToString(a.hierConf,1),
      a.channelOK?"1":"0",a.volumeOK?"1":"0",a.alternationOK?"1":"0",a.degreeOK?"1":"0",a.innerOK?"1":"0",
      DoubleToString(a.sMomentum,0),a.state,res,DoubleToString(rm,2));
   FileClose(h);
}
void LogSignalIfChanged(const Analy &a){
   if(!InpLogSignals||!a.avail)return;
   int idx=TFIdx(a.tf);if(idx<0)return;
   string cur=a.state;
   if(cur=="NO SETUP"||cur=="NO DATA"||cur=="CONFIRMING")return;
   if(g_lastLoggedState[idx]!=cur){
      g_lastLoggedState[idx]=cur;
      if(cur=="CONFIRMED"||cur=="TP1 REACHED"||cur=="STOP HIT"||cur=="INVALIDATED"||cur=="EXPIRED")LogSignal(a);
   }
}
// v14.4 OPTIMIZED: Chunked growth for trades array
int CollectTrades(ENUM_TIMEFRAMES tf,int bL,int mP,WFTrade &tr[]){
   ArrayResize(tr,0);
   MqlRates rates[];double atr[];int cnt=0;
   if(!LoadRates(tf,bL,rates,cnt))return 0;
   if(!BuildATR(rates,cnt,atr))return 0;
   Pivot pv[];
   if(!BuildAdaptivePivots(rates,atr,cnt,mP,pv))return 0;
   int total=ArraySize(pv);if(total<10)return 0;
   PrepareCorrCache(pv,total,tf);ComputeAltRun(pv,total);
   int estCap=MathMax(CHUNK_MIN,MathMin(2000,total/50));
   ArrayResize(tr,estCap);
   int tCap=estCap;
   int s=0,tC=0;
   while(s<total-3){
      if(s>=ArraySize(g_altRun)||g_altRun[s]<4){s++;continue;}
      Candidate best;ResetCand(best);
      if(!BestCand(pv,total,s,6,best)){
         if(!BestCand(pv,total,s,5,best)){
            if(!BestCand(pv,total,s,4,best)){s++;continue;}
         }
      }
      if(!best.valid||best.pat==P_SWING){s++;continue;}
      RunScoring(best,pv,tf);
      if(!best.hardRules||best.composite<InpMinScore){s=best.e+1;continue;}
      int fd=FutureDir(best.pat,best.dir,best.preDir);
      if(fd==0){s=best.e+1;continue;}
      int rd=pv[best.e].confirmedBar;
      if(rd+1>=cnt){s=best.e+1;continue;}
      double en=rates[rd].close;
      double lo=pv[best.s].price,hi=lo;
      for(int i=best.s;i<=best.e;i++){lo=MathMin(lo,pv[i].price);hi=MathMax(hi,pv[i].price);}
      double pad=MathMax(atr[rd]*0.25,_Point*5.0);
      double iv=(fd>0)?lo-pad:hi+pad;
      double bs=0;
      if(IsImpulse(best.pat)&&best.n>=6)bs=MathAbs(pv[best.s+5].price-pv[best.s].price);
      else if(best.n>=4)bs=MathAbs(pv[best.s+3].price-pv[best.s+2].price);
      if(bs<=0){s=best.e+1;continue;}
      double tp=en+fd*bs*0.618;
      double rk=MathAbs(en-iv),rw=MathAbs(tp-en);
      if(rk<=_Point||rw<=_Point){s=best.e+1;continue;}
      string oc="";
      for(int b=rd+1;b<cnt;b++){
         bool st=fd>0?rates[b].low<=iv:rates[b].high>=iv;
         bool hi2=fd>0?rates[b].high>=tp:rates[b].low<=tp;
         if(st){oc="LOSS";break;}
         if(hi2){oc="WIN";break;}
         if(b-rd>InpHorizonBars){oc="FLAT";break;}
      }
      if(oc==""){s=best.e+1;continue;}
      if(tC>=tCap){tCap=tCap+MathMax(CHUNK_MIN,tCap/2);ArrayResize(tr,tCap);}
      WFTrade t;t.t=rates[rd].time;t.valid=true;
      t.entry=en;t.sl=iv;t.tp=tp;
      if(oc=="WIN"){t.win=true;t.r=rw/rk;}
      else if(oc=="LOSS"){t.win=false;t.r=-1.0;}
      else{t.win=false;t.r=0.0;}
      tr[tC++]=t;
      s=best.e+1;
   }
   if(tC<ArraySize(tr))ArrayResize(tr,tC);
   return tC;
}
void ComputeWFStats(WFTrade &tr[],int f,int t,double &wr,double &pf,int &cnt){
   int w=0,l=0,tt=0;double sw=0,sl=0;int n=ArraySize(tr);
   for(int i=f;i<t&&i<n;i++){
      if(!tr[i].valid)continue;
      tt++;
      if(tr[i].r>0){w++;sw+=tr[i].r;}
      else if(tr[i].r<0){l++;sl+=MathAbs(tr[i].r);}
   }
   cnt=tt;wr=(tt>0)?100.0*(double)w/(double)tt:0.0;
   pf=(sl>0)?(sw/sl):(sw>0?999.0:0.0);
}
void RunWalkForward(){
   Print("EWQ v14.4 WF: starting...");
   ENUM_TIMEFRAMES tf=GetChartTF();
   WFTrade tr[];
   int n=CollectTrades(tf,InpWFBarsCount,InpMaxChartPivots,tr);
   if(n<30){PrintFormat("EWQ WF: insufficient trades (%d)",n);g_wfResultX.valid=false;return;}
   int split=(int)((double)n*(double)InpWFInSamplePct/100.0);
   if(split<15)split=15;if(split>n-15)split=n-15;
   double isWR=0,isPF=0;int isC=0;
   ComputeWFStats(tr,0,split,isWR,isPF,isC);
   double oWR=0,oPF=0;int oC=0;
   ComputeWFStats(tr,split,n,oWR,oPF,oC);
   double cons=0;
   if(isPF>0&&oPF>0)cons=(MathMin(isPF,oPF)/MathMax(isPF,oPF))*100.0;
   g_wfResultX.isWinRate=isWR;g_wfResultX.oosWinRate=oWR;
   g_wfResultX.isProfitFactor=isPF;g_wfResultX.oosProfitFactor=oPF;
   g_wfResultX.consistency=cons;
   g_wfResultX.tradesIS=isC;g_wfResultX.tradesOOS=oC;
   g_wfResultX.valid=true;
   PrintFormat("EWQ WF: IS %d WR=%.1f%% PF=%.2f | OOS %d WR=%.1f%% PF=%.2f | Cons=%.1f%%",isC,isWR,isPF,oC,oWR,oPF,cons);
   bool wins[];ArrayResize(wins,n);
   double rr[];ArrayResize(rr,n);
   double eq[];ArrayResize(eq,n+1);eq[0]=1000.0;
   for(int i=0;i<n;i++){wins[i]=tr[i].win;rr[i]=tr[i].r;eq[i+1]=eq[i]+tr[i].r*100.0;}
   double sh=CalcSharpe(rr),so=CalcSortino(rr),dd=CalcMaxDD(eq);
   double cal=(dd>0)?(CalcMean(rr)*252.0/dd):0;
   BootstrapCI bci=BootstrapWinRate(wins,1000);
   double aw=0,al=0;int wc=0,lc=0;
   for(int i=0;i<n;i++){if(tr[i].r>0){aw+=tr[i].r;wc++;}else if(tr[i].r<0){al+=MathAbs(tr[i].r);lc++;}}
   if(wc>0)aw/=wc;if(lc>0)al/=lc;
   double wr2=(wc>0||lc>0)?(double)wc/(double)(wc+lc):0.0;
   MonteCarloResult mc=RunMonteCarlo(wr2,aw,al,1000);
   PrintFormat("EWQ STATS: Sharpe=%.2f Sortino=%.2f MaxDD=%.1f%% Calmar=%.2f",sh,so,dd,cal);
   PrintFormat("EWQ BOOTSTRAP: WR=%.1f%% [%.1f%%-%.1f%%]",bci.mean,bci.lower,bci.upper);
   PrintFormat("EWQ MC: Avg=%.0f Worst=%.0f Best=%.0f AvgDD=%.1f%%",mc.avgFinal,mc.worstCase,mc.bestCase,mc.avgDD);
}
#define DASH_W 620
#define DASH_HDR 50
#define DASH_ROW 18
#define DASH_PAD 12
int DashHeight(){int ex=0;if(g_wfResultX.valid)ex=22;return DASH_HDR+26+g_tfCount*DASH_ROW+80+ex;}
int DashX(){
   long cw=ChartGetInteger(0,CHART_WIDTH_IN_PIXELS);
   int x=InpDashX;
   if(g_dashRightState)x=(int)cw-DASH_W-InpDashX;
   if(x<5)x=5;
   return x;
}
int DashY(){int y=InpDashY;if(y<40)y=40;return y;}
void DrawDashButtons(){
   int x=InpBtnX;int y=InpBtnY;int h=InpBtnH;
   string st;color cl;
   if(g_dashMode==0){st="[DASH: RIGHT >]";cl=C'0,195,255';}
   else if(g_dashMode==1){st="[DASH: LEFT <]";cl=C'255,200,40';}
   else{st="[DASH: HIDDEN x]";cl=C'255,80,80';}
   BtnV14(g_btnCycle,st,x,y,InpBtnW,h,cl);
}
void DrawDashV14(){
   if(g_dashMode==2||!g_dashVisState){
      ObjectDelete(0,g_pfx+"D14BG");
      ObjectDelete(0,g_pfx+"D14T");
      ObjectDelete(0,g_pfx+"D14S");
      ObjectDelete(0,g_pfx+"D14H1");ObjectDelete(0,g_pfx+"D14H2");
      ObjectDelete(0,g_pfx+"D14H3");ObjectDelete(0,g_pfx+"D14H4");
      ObjectDelete(0,g_pfx+"D14H5");
      ObjectDelete(0,g_pfx+"D14OV");ObjectDelete(0,g_pfx+"D14INFO");
      ObjectDelete(0,g_pfx+"D14WF");
      for(int k=0;k<MAX_TF;k++){
         ObjectDelete(0,g_pfx+"D14T_"+IntegerToString(k));
         ObjectDelete(0,g_pfx+"D14P_"+IntegerToString(k));
         ObjectDelete(0,g_pfx+"D14R_"+IntegerToString(k));
         ObjectDelete(0,g_pfx+"D14S_"+IntegerToString(k));
         ObjectDelete(0,g_pfx+"D14ST_"+IntegerToString(k));
      }
      DrawDashButtons();return;
   }
   int x=DashX(),y=DashY();
   int w=DASH_W,h=DashHeight();
   color bgC=C'8,12,20',bdC=C'60,80,110';
   color txtC=C'235,240,248',accC=C'0,195,255';
   color grnC=C'0,255,145',redC=C'255,80,80';
   color goldC=C'255,200,40',dimC=C'70,85,105';
   if(ObjectFind(0,g_pfx+"D14BG")<0){
      ObjectCreate(0,g_pfx+"D14BG",OBJ_RECTANGLE_LABEL,0,0,0);
      ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_CORNER,CORNER_LEFT_UPPER);
      ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_BORDER_TYPE,BORDER_FLAT);
      ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_SELECTABLE,false);
      ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_HIDDEN,true);
   }
   ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_XDISTANCE,x);
   ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_YDISTANCE,y);
   ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_XSIZE,w);
   ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_YSIZE,h);
   ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_BGCOLOR,bgC);
   ObjectSetInteger(0,g_pfx+"D14BG",OBJPROP_COLOR,bdC);
   SLbl(g_pfx+"D14T",x+DASH_PAD,y+8,accC,11,"EWQ v14.4 - Elliott Quant PRO");
   SLbl(g_pfx+"D14S",x+DASH_PAD,y+28,goldC,8,_Symbol+" | "+TFName(g_curTF));
   int hY=y+DASH_HDR;
   SLbl(g_pfx+"D14H1",x+DASH_PAD,hY,txtC,8,"TF");
   SLbl(g_pfx+"D14H2",x+DASH_PAD+50,hY,txtC,8,"PATTERN");
   SLbl(g_pfx+"D14H3",x+DASH_PAD+180,hY,txtC,8,"DIR");
   SLbl(g_pfx+"D14H4",x+DASH_PAD+230,hY,txtC,8,"SCORE");
   SLbl(g_pfx+"D14H5",x+DASH_PAD+300,hY,txtC,8,"STATE");
   int rY=hY+18;
   for(int i=0;i<g_tfCount;i++){
      ENUM_TIMEFRAMES tf=g_tfList[i];Analy a=g_mtf[i];
      bool ic=(tf==g_curTF);
      color rc=ic?clrYellow:txtC;
      string pat="-",tr="-",sc="-",st="-";
      if(a.avail){pat=PatName(a.pat);tr=(a.futDir>0)?"UP":((a.futDir<0)?"DN":"-");sc=DoubleToString(a.quality,0)+"/100";st=a.state;}
      int rowY=rY+i*DASH_ROW;
      SLbl(g_pfx+"D14T_"+IntegerToString(i),x+DASH_PAD,rowY,rc,8,(ic?"> ":"  ")+TFName(tf));
      SLbl(g_pfx+"D14P_"+IntegerToString(i),x+DASH_PAD+50,rowY,rc,8,pat);
      SLbl(g_pfx+"D14R_"+IntegerToString(i),x+DASH_PAD+180,rowY,a.futDir>0?grnC:(a.futDir<0?redC:dimC),8,tr);
      SLbl(g_pfx+"D14S_"+IntegerToString(i),x+DASH_PAD+230,rowY,rc,8,sc);
      SLbl(g_pfx+"D14ST_"+IntegerToString(i),x+DASH_PAD+300,rowY,a.state=="CONFIRMED"?grnC:(a.state=="INVALIDATED"?redC:goldC),8,st);
   }
   for(int k=g_tfCount;k<MAX_TF;k++){
      ObjectDelete(0,g_pfx+"D14T_"+IntegerToString(k));
      ObjectDelete(0,g_pfx+"D14P_"+IntegerToString(k));
      ObjectDelete(0,g_pfx+"D14R_"+IntegerToString(k));
      ObjectDelete(0,g_pfx+"D14S_"+IntegerToString(k));
      ObjectDelete(0,g_pfx+"D14ST_"+IntegerToString(k));
   }
   int cY=rY+g_tfCount*DASH_ROW+8;
   color ovC=(g_cons.overallAlign==A_GREEN)?grnC:(g_cons.overallAlign==A_RED)?redC:goldC;
   SLbl(g_pfx+"D14OV",x+DASH_PAD,cY,ovC,9,"Signal: "+AlignText(g_cons.overallAlign)+"   Agree: "+DoubleToString(g_cons.weightedAgree,0)+"%");
   int iY=cY+22;
   SLbl(g_pfx+"D14INFO",x+DASH_PAD,iY,dimC,7,"Strict:"+(InpStrictFibonacci?"Y":"N")+" Chan:"+(InpEnforceChanneling?"Y":"N")+" Mom:"+(InpUseMomentumDiv?"Y":"N")+" FVG:"+(InpUseFVG?"Y":"N"));
   int stY=iY+18;
   if(g_wfResultX.valid){
      SLbl(g_pfx+"D14WF",x+DASH_PAD,stY,accC,8,StringFormat("WF: IS PF=%.2f | OOS PF=%.2f | Cons=%.0f%%",g_wfResultX.isProfitFactor,g_wfResultX.oosProfitFactor,g_wfResultX.consistency));
   }else{
      SLbl(g_pfx+"D14WF",x+DASH_PAD,stY,dimC,8,"WF: not run yet");
   }
   DrawDashButtons();
}
void SendTelegram(string message){
   if(!InpUseTelegram)return;
   if(InpTelegramToken==""||InpTelegramChatID=="")return;
   Print("Telegram would send: ",message);
}
void FireAlert(string title,string body){
   if(!InpAlertsEnabled)return;
   datetime now=TimeLocal();
   if(now-g_lastAlertTime<InpAlertCooldown)return;
   string key=title+"|"+body;
   if(key==g_lastAlertKey&&now-g_lastAlertTime<InpAlertCooldown*2)return;
   g_lastAlertTime=now;g_lastAlertKey=key;
   string msg=title+" | "+_Symbol+" | "+body;
   if(InpAlertPopup)Alert(msg);
   if(InpAlertSound)PlaySound(InpAlertSoundFile);
   if(InpAlertPush)SendNotification(msg);
   if(InpUseTelegram)SendTelegram(msg);
   Print("[EWQ ALERT] ",msg);
}
void CheckAlertsV14(){
   if(!InpAlertsEnabled)return;
   static string lastCK="";
   if(g_cons.tradeReady&&g_chart.avail&&g_chart.qualified){
      string key=TFName(g_curTF)+"_"+IntegerToString((long)g_chart.readyTime)+"_"+IntegerToString((int)g_chart.pat);
      if(key!=lastCK){
         string body=(g_chart.futDir>0?"BUY":"SELL")+" | Entry="+DoubleToString(g_chart.entry,_Digits)+" | SL="+DoubleToString(g_chart.tradeSL,_Digits)+" | TP1="+DoubleToString(g_chart.tp1,_Digits)+" | Score="+DoubleToString(g_chart.quality,0);
         FireAlert("CONFIRMED",body);
         lastCK=key;
      }
   }
}
void DrawAll(){
   uint t0=GetTickCount();
   EnsureFutureSpace();
   DrawHistorical();
   DrawCurrent();
   DrawFuture();
   DrawSignalBox();
   DrawDashV14();
   PruneAllFamilies();
   ChartRedraw(0);
   PerfLog("DrawAll",GetTickCount()-t0);
}
bool ApplyLiveInvalidation(){
   bool ch=false;
   for(int i=0;i<g_tfCount;i++){
      if(!g_mtf[i].avail||g_mtf[i].futDir==0||g_mtf[i].basis<=0)continue;
      double hi=iHigh(_Symbol,g_tfList[i],0);
      double lo=iLow(_Symbol,g_tfList[i],0);
      if(hi==0&&lo==0)continue;
      int d=g_mtf[i].futDir;
      bool inv=d>0?lo<=g_mtf[i].inval:hi>=g_mtf[i].inval;
      bool st=d>0?lo<=g_mtf[i].tradeSL:hi>=g_mtf[i].tradeSL;
      bool h=d>0?hi>=g_mtf[i].tp1:lo<=g_mtf[i].tp1;
      if(inv&&g_mtf[i].structureValid){
         g_mtf[i].structureValid=false;g_mtf[i].active=false;g_mtf[i].qualified=false;
         g_mtf[i].state="INVALIDATED";ch=true;
      }else if(g_mtf[i].active&&(st||h)){
         g_mtf[i].active=false;g_mtf[i].qualified=false;
         g_mtf[i].state=st?"STOP HIT":"TP1 REACHED";ch=true;
      }
   }
   if(ch)ComputeConsensus();
   int ci=TFIdx(g_curTF);
   if(ci>=0&&g_mtf[ci].avail)g_chart=g_mtf[ci];
   return ch;
}
void RefreshChart(bool force){
   if(!g_init||g_busy)return;
   bool ch=force||!g_chartReady;
   for(int i=0;i<g_tfCount;i++)if(iTime(_Symbol,g_tfList[i],1)!=g_seenClosed[i])ch=true;
   if(!ch)return;
   g_busy=true;
   g_curTF=GetChartTF();
   g_lastBar=iTime(_Symbol,g_curTF,0);
   AnalyzeDashboard();
   AnalyzeCurrentChart();
   ApplyLiveInvalidation();
   DrawAll();
   if(g_logEnabled)for(int i=0;i<g_tfCount;i++)LogSignalIfChanged(g_mtf[i]);
   g_busy=false;
}
void RefreshDashboard(bool force){
   if(force||TimeLocal()-g_lastRefresh>=InpRefreshSec)RefreshChart(true);
   else RefreshChart(false);
}
bool DefensiveInitCheck(){
   int b=(int)TerminalInfoInteger(TERMINAL_BUILD);
   if(b<MIN_BUILD){PrintFormat("EWQ FATAL: build %d < %d",b,MIN_BUILD);return false;}
   if(!SymbolSelect(_Symbol,true)){PrintFormat("EWQ FATAL: symbol %s",_Symbol);return false;}
   return true;
}
int OnInit(){
   if(InpATRPeriod<2||InpPivotMult<=0||InpChartBars<0||InpMTFBars<80||
      InpMaxChartPivots<6||InpMaxMTFPivots<6||InpConfirmDelay<0||
      InpRefreshSec<1||InpHorizonBars<1||InpMaxEntryAgeBars<0||
      InpMinScore<0||InpMinScore>100||InpMinEntryScore<0||InpMinEntryScore>100||
      InpMinSubScore<0||InpMinSubScore>100||InpHierMinScore<0||InpHierMinScore>100||
      InpMinRR<=0||InpTradeStopATR<=0||InpProjectionBars<12){
      Print("EWQ: invalid inputs");return INIT_PARAMETERS_INCORRECT;
   }
   if(!DefensiveInitCheck())return INIT_FAILED;
   PrintFormat("EWQ v%s MAX: OnInit START | %s | %s",EWQ_VER,_Symbol,TFName(GetChartTF()));
   g_init=false;g_chartReady=false;
   g_curTF=GetChartTF();
   g_lastBar=0;g_lastRefresh=0;g_lastClosedBar=0;
   ArrayResize(g_chartPiv,0);ArrayResize(g_chartMap,0);
   ArrayResize(g_corrCache,0);ArrayResize(g_altRun,0);
   ArrayResize(g_segBuffer,0);g_segCap=0;
   g_corrCacheTot=0;g_corrCacheSym="";g_altRunTot=0;
   ResetAllCounters();
   g_pfx="EWQ144_"+IntegerToString(ChartID())+"_"+IntegerToString((long)GetMicrosecondCount())+"_";
   g_btnCycle=g_pfx+"BTN_CYCLE";
   g_lastClickTick=0;g_lastClickName="";
   if(!InpShowDashV14)g_dashMode=2;
   else if(InpDashRight)g_dashMode=0;
   else g_dashMode=1;
   g_dashVisState=(g_dashMode!=2);
   g_dashRightState=(g_dashMode==0);
   g_oldShift=(bool)ChartGetInteger(0,CHART_SHIFT);
   g_oldShiftSize=ChartGetDouble(0,CHART_SHIFT_SIZE);
   g_firstRun=true;
   g_isOffline=(bool)ChartGetInteger(0,CHART_IS_OFFLINE);
   if(g_isOffline)Print("EWQ: offline chart detected");
   g_activePivotMult=InpPivotMult;g_activeATRPeriod=InpATRPeriod;
   g_activeMinRR=InpMinRR;g_activeMinScore=InpMinEntryScore;
   g_activeMinSub=InpMinSubScore;g_activeHierMin=InpHierMinScore;
   g_logEnabled=InpLogSignals;g_logFileName=InpLogFileName;
   g_wfResultX.valid=false;
   BuildTFList();
   g_lastSymbol=_Symbol;
   ApplyAutoProfile(true);
   for(int i=0;i<MAX_TF;i++){
      g_cache[i].count=0;g_cache[i].ready=false;
      g_cache[i].atr=0;g_cache[i].stamp=0;
      g_seenClosed[i]=0;g_cachedEMAReady[i]=false;
      g_tfNodeIdx[i]=-1;g_lastLoggedState[i]="";
      ResetAnaly(g_mtf[i],PERIOD_M15);
   }
   ResetTree();
   IndicatorSetString(INDICATOR_SHORTNAME,"EWQ v"+EWQ_VER+" MAX");
   if(g_logEnabled)EnsureLogHeader();
   g_init=true;
   EnsureFutureSpace();
   ChartSetInteger(0,CHART_BRING_TO_TOP,true);
   ChartSetInteger(0,CHART_FOREGROUND,true);
   ChartRedraw(0);
   EventSetTimer(1);
   PrintFormat("EWQ v%s ready | 1 cycle button | Chunked arrays | TFs=%d",EWQ_VER,g_tfCount);
   return INIT_SUCCEEDED;
}
void OnDeinit(const int reason){
   EventKillTimer();
   ClearObjects();
   ResetAllCounters();
   if(g_init&&InpAutoShift){
      ChartSetInteger(0,CHART_SHIFT,g_oldShift);
      ChartSetDouble(0,CHART_SHIFT_SIZE,g_oldShiftSize);
   }
   for(int i=0;i<MAX_TF;i++){
      g_cache[i].count=0;g_cache[i].ready=false;
      g_seenClosed[i]=0;g_cachedEMAReady[i]=false;g_tfNodeIdx[i]=-1;
   }
   ArrayResize(g_chartPiv,0);ArrayResize(g_chartMap,0);
   ArrayResize(g_corrCache,0);ArrayResize(g_altRun,0);
   ArrayResize(g_segBuffer,0);
   ResetTree();
   g_init=false;g_chartReady=false;
   ChartRedraw(0);
   PrintFormat("EWQ v%s: OnDeinit reason=%d",EWQ_VER,reason);
}
int OnCalculate(const int rates_total,const int prev_calculated,
                const datetime &time[],const double &open[],
                const double &high[],const double &low[],
                const double &close[],const long &tick_volume[],
                const long &volume[],const int &spread[]){
   if(!g_init||g_busy)return rates_total;
   datetime curClosed=iTime(_Symbol,g_curTF,1);
   if(curClosed==g_lastClosedBar&&prev_calculated!=0)return rates_total;
   g_lastClosedBar=curClosed;
   RefreshChart(prev_calculated==0);
   if(ApplyLiveInvalidation())DrawAll();
   return rates_total;
}
void OnTimer(){
   if(!g_init||g_busy)return;
   if(g_firstRun){
      g_firstRun=false;
      g_curTF=GetChartTF();
      AnalyzeDashboard();
      AnalyzeCurrentChart();
      DrawAll();
      PrintFormat("EWQ v14.4: initial scan complete (TFs=%d)",g_tfCount);
      if(InpRunWFOnStart)RunWalkForward();
      return;
   }
   RefreshDashboard(false);
   if(ApplyLiveInvalidation())DrawAll();
   CheckAlertsV14();
}
void OnChartEvent(const int id,const long &lparam,const double &dparam,const string &sparam){
   if(!g_init)return;
   if(id==CHARTEVENT_OBJECT_CLICK){
      ObjectSetInteger(0,sparam,OBJPROP_STATE,false);
      ObjectSetInteger(0,sparam,OBJPROP_SELECTED,false);
      uint now=GetTickCount();
      if(sparam==g_lastClickName&&(now-g_lastClickTick)<300){ChartRedraw(0);return;}
      g_lastClickName=sparam;g_lastClickTick=now;
      if(sparam==g_btnCycle){
         g_dashMode=(g_dashMode+1)%3;
         g_dashVisState=(g_dashMode!=2);
         g_dashRightState=(g_dashMode==0);
         PrintFormat("EWQ UI: MODE -> %s",(g_dashMode==0)?"RIGHT":(g_dashMode==1)?"LEFT":"HIDDEN");
         DrawDashV14();
         ChartRedraw(0);
         return;
      }
      return;
   }
   if(id==CHARTEVENT_CHART_CHANGE){
      if(_Symbol!=g_lastSymbol){
         g_lastSymbol=_Symbol;
         ApplyAutoProfile(true);
         g_lastRefresh=0;
         for(int i=0;i<MAX_TF;i++)g_seenClosed[i]=0;
         RefreshChart(true);
         return;
      }
      ENUM_TIMEFRAMES tf=GetChartTF();
      if(tf!=g_curTF){
         if(!TFInList(tf)){AddTFIfMissing(tf);SortTFList();}
         g_curTF=tf;g_lastBar=0;
         RefreshChart(true);
      }else{
         DrawAll();
      }
      return;
   }
}
//+------------------------------------------------------------------+
//| END EWQ v14.4 - Production Ready                                 |
//+------------------------------------------------------------------+