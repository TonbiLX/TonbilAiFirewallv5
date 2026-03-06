plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.serialization) apply false
    alias(libs.plugins.compose.compiler) apply false
    // DIKKAT: kotlin-android eklentisi YOK — AGP 9.0 dahili yonetiyor
}
