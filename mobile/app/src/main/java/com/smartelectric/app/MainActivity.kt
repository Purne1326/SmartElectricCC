package com.smartelectric.app

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController

import com.smartelectric.app.ui.screens.DashboardScreen
import com.smartelectric.app.ui.screens.AnalyticsScreen
import com.smartelectric.app.ui.screens.ControlScreen
import com.smartelectric.app.ui.screens.SystemLogsScreen
import com.smartelectric.app.ui.screens.SettingsScreen
import com.smartelectric.app.ui.theme.SmartElectricTheme

sealed class Screen(val route: String, val title: String, val icon: ImageVector) {
    object Dashboard : Screen("dashboard", "Dashboard", Icons.Default.Home)
    object Control : Screen("control", "Control", Icons.Default.PlayArrow)
    object Analytics : Screen("analytics", "Analytics", Icons.Default.Info)
    object Logs : Screen("logs", "Logs", Icons.Default.List)
    object Settings : Screen("settings", "Settings", Icons.Default.Settings)
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SmartElectricTheme {
                MainAppScreen(this)
            }
        }
    }
}

@Composable
fun MainAppScreen(context: Context) {
    val navController = rememberNavController()
    val items = listOf(
        Screen.Dashboard,
        Screen.Control,
        Screen.Analytics,
        Screen.Logs,
        Screen.Settings
    )

    // Load API gateway IP from SharedPreferences (Defaults to 192.168.0.39)
    val sharedPref = context.getSharedPreferences("SmartElectricPrefs", Context.MODE_PRIVATE)
    var gatewayIp by remember { 
        mutableStateOf(sharedPref.getString("gateway_ip", "192.168.0.39") ?: "192.168.0.39") 
    }

    Scaffold(
        bottomBar = {
            NavigationBar {
                val navBackStackEntry by navController.currentBackStackEntryAsState()
                val currentRoute = navBackStackEntry?.destination?.route
                items.forEach { screen ->
                    NavigationBarItem(
                        icon = { Icon(screen.icon, contentDescription = screen.title) },
                        label = { Text(screen.title) },
                        selected = currentRoute == screen.route,
                        onClick = {
                            navController.navigate(screen.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    )
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Dashboard.route,
            modifier = Modifier.fillMaxSize().padding(innerPadding)
        ) {
            composable(Screen.Dashboard.route) {
                DashboardScreen(gatewayIp)
            }
            composable(Screen.Control.route) {
                ControlScreen(gatewayIp)
            }
            composable(Screen.Analytics.route) {
                AnalyticsScreen(gatewayIp)
            }
            composable(Screen.Logs.route) {
                SystemLogsScreen(gatewayIp)
            }
            composable(Screen.Settings.route) {
                SettingsScreen(
                    currentIp = gatewayIp,
                    onIpSaved = { newIp ->
                        gatewayIp = newIp
                        sharedPref.edit().putString("gateway_ip", newIp).apply()
                    }
                )
            }
        }
    }
}
