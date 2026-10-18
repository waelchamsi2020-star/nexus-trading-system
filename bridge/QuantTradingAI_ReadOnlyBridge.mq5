#property strict
#property version "1.00"
#property description "Read-only sessions and economic calendar exporter. Contains NO trade functions."

input int RefreshSeconds=30;

string J(string s) {
   StringReplace(s,"\\","\\\\"); StringReplace(s,"\"","\\\"");
   StringReplace(s,"\r","\\r");StringReplace(s,"\n","\\n");StringReplace(s,"\t","\\t");
   return "\""+s+"\"";
}
string B(bool b) {return b?"true":"false";}
string N(long n) {return IntegerToString(n);}
string V(long n) {return n==LONG_MIN?"null":DoubleToString((double)n/1000000.0,6);}

int OnInit() { EventSetTimer(MathMax(10,RefreshSeconds)); Export(); return INIT_SUCCEEDED; }
void OnDeinit(const int reason) { EventKillTimer(); }
void OnTick() {} // Deliberately no trading logic.
void OnTimer() { Export(); }

void Export() {
   datetime utc=TimeGMT(), server=TimeTradeServer();
   bool connected=(bool)TerminalInfoInteger(TERMINAL_CONNECTED);
   long raw_offset=(long)server-(long)utc;
   long offset=(long)MathRound((double)raw_offset/900.0)*900;
   bool clock_ok=MathAbs((double)(raw_offset-offset))<120 && MathAbs((double)offset)<=50400;
   MqlDateTime dt; TimeToStruct(server,dt); int sec=dt.hour*3600+dt.min*60+dt.sec;
   string sessions="{";
   int total=SymbolsTotal(false);
   for(int i=0;i<total;i++) {
      string name=SymbolName(i,false); bool known=false,open=false,ambiguous=false; string windows="["; int count=0;
      for(int prev=0;prev<2;prev++) {
         ENUM_DAY_OF_WEEK day=(ENUM_DAY_OF_WEEK)((dt.day_of_week+7-prev)%7);
         for(uint index=0;index<64;index++) {
            datetime from,to;
            if(!SymbolInfoSessionTrade(name,day,index,from,to)) break;
            long a=(long)from%86400,b=(long)to;
            if(b>=86400) b=86400; else b=b%86400;
            if(prev==0) {
               known=true;
               if(count++>0) windows+=",";
               windows+="{\"from\":"+N(a)+",\"to\":"+N(b)+"}";
               if(a==b) ambiguous=true; // Equal endpoints without a day offset have unknown duration.
               else if(b>a && sec>=a && sec<b) open=true;
               else if(b<a && sec>=a) open=true;
            } else if(b<a && sec<b) {open=true;known=true;}
         }
      }
      windows+="]";
      if(i>0) sessions+=",";
      sessions+=J(name)+":{\"known\":"+B(known && clock_ok && !ambiguous)+",\"open\":"+B(open && connected && clock_ok && !ambiguous)+",\"sessions\":"+windows+",\"reason\":"+J(ambiguous?"Ambiguous equal-endpoint session":known?"Broker session schedule":"No trade session returned")+"}";
   }
   sessions+="}";
   datetime from_server=server-86400, to_server=server+172800;
   MqlCalendarValue values[]; ResetLastError();
   int found=CalendarValueHistory(values,from_server,to_server); int calendar_error=GetLastError();
   string events="["; bool calendar_ok=found>=0 && clock_ok && connected; int emitted=0;
   for(int k=0;k<found;k++) {
      MqlCalendarEvent event; MqlCalendarCountry country;
      if(!CalendarEventById(values[k].event_id,event) || !CalendarCountryById(event.country_id,country)) {calendar_ok=false;continue;}
      if(emitted++>0) events+=",";
      events+="{\"id\":"+N((long)values[k].id)+",\"event_id\":"+N((long)event.id)+",\"title\":"+J(event.name)+
         ",\"source_url\":"+J(event.source_url)+",\"provider\":\"MT5 Economic Calendar\",\"currency\":"+J(country.currency)+
         ",\"country\":"+J(country.code)+",\"time_utc\":"+N((long)values[k].time-offset)+",\"server_time\":"+N((long)values[k].time)+
         ",\"time_mode\":"+N((long)event.time_mode)+",\"importance\":"+N((long)event.importance)+
         ",\"actual\":"+V(values[k].actual_value)+",\"forecast\":"+V(values[k].forecast_value)+
         ",\"previous\":"+V(values[k].prev_value)+",\"revised_previous\":"+V(values[k].revised_prev_value)+
         ",\"revision\":"+N((long)values[k].revision)+",\"unit\":"+N((long)event.unit)+",\"multiplier\":"+N((long)event.multiplier)+
         ",\"event_time\":"+N((long)values[k].time-offset)+",\"published_at\":null,\"received_at\":"+N((long)utc)+
         ",\"timezone\":\"UTC\",\"facts\":"+J(event.name)+",\"interpretation\":\"Potential macroeconomic exposure; no inferred direction\"}";
   }
   events+="]";
   MqlCalendarCountry countries[]; int countries_count=CalendarCountries(countries); string currencies="[";
   if(countries_count<0) calendar_ok=false;
   string seen="|";int n=0;
   for(int c=0;c<countries_count;c++) {
      string currency=countries[c].currency;
      if(StringLen(currency)==0 || StringFind(seen,"|"+currency+"|")>=0) continue;
      seen+=currency+"|"; if(n++>0) currencies+=",";currencies+=J(currency);
   }
   currencies+="]";
   string calendar="{\"ok\":"+B(calendar_ok)+",\"known\":"+B(calendar_ok)+",\"coverage_known\":"+B(calendar_ok)+
      ",\"as_of\":"+N((long)utc)+",\"from_utc\":"+N((long)from_server-offset)+",\"to_utc\":"+N((long)to_server-offset)+
      ",\"currencies\":"+currencies+",\"events\":"+events+",\"error\":"+N(calendar_error)+",\"provider\":\"MT5 Economic Calendar\"}";
   string output="{\"schema\":1,\"as_of\":"+N((long)utc)+",\"server_offset_seconds\":"+N(offset)+",\"clock_ok\":"+B(clock_ok)+
      ",\"login\":"+N(AccountInfoInteger(ACCOUNT_LOGIN))+",\"server\":"+J(AccountInfoString(ACCOUNT_SERVER))+
      ",\"terminal_path\":"+J(TerminalInfoString(TERMINAL_PATH))+",\"connected\":"+B(connected)+",\"sessions\":"+sessions+",\"calendar\":"+calendar+"}";
   // Write the published file directly. Some MT5 builds keep the destination
   // open briefly while external readers inspect it, which made the previous
   // temp-file FileMove fail with error 5004 and left stale bridge data.
   // Readers already reject incomplete JSON and retry on the next refresh.
   int handle=FileOpen("NEXUS_bridge.json",FILE_WRITE|FILE_TXT|FILE_ANSI,0,CP_UTF8);
   if(handle==INVALID_HANDLE) {Print("NEXUS bridge FileOpen failed: ",GetLastError());return;}
   FileWriteString(handle,output);FileFlush(handle);FileClose(handle);
}
