package com.levi.reminders;

import android.os.Bundle;
import android.webkit.WebView;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(LeviAlarmPlugin.class);
        registerPlugin(LeviAlarmManagerPlugin.class);
        super.onCreate(savedInstanceState);

        // Disable overscroll glow effect on WebView (like iOS bounce disable)
        WebView webView = getBridge().getWebView();
        if (webView != null) {
            webView.setOverScrollMode(WebView.OVER_SCROLL_NEVER);
        }
    }
}
