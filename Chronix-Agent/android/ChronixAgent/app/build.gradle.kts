plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.chronix.agent"
    compileSdk = 34

    defaultConfig {
        applicationId = "com.chronix.agent"
        minSdk = 24
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
        // NOTE: no Gemini API key or any secret is defined here or anywhere
        // in this module. The APK talks only to the paired Chronix Agent
        // on the LAN, never directly to Gemini. See README "Security".
    }

    buildTypes {
        release {
            // Minification/R8 is intentionally OFF for now. Compose +
            // DataStore need carefully tuned keep rules to survive R8
            // shrinking, and getting that wrong fails the CI build with
            // opaque R8 errors rather than a clear test failure. Once the
            // app is stable, minification can be re-enabled alongside a
            // real proguard-rules.pro tuned against actual R8 output.
            isMinifyEnabled = false
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    buildFeatures {
        compose = true
    }
    composeOptions {
        kotlinCompilerExtensionVersion = "1.5.4"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.12.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.7.0")
    implementation("androidx.activity:activity-compose:1.8.2")
    implementation(platform("androidx.compose:compose-bom:2024.02.00"))
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.material:material-icons-extended")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.datastore:datastore-preferences:1.0.0")
    // Deliberately no OkHttp/Retrofit/Gson dependency pulled in for this
    // minimal build - HttpURLConnection + org.json (both in the Android
    // SDK already) keep the APK small. Can be swapped later if the
    // project grows.
    debugImplementation("androidx.compose.ui:ui-tooling")
}
