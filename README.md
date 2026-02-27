# BMA Messenger (Android)

## Dependencies

### Build and toolchain
- Android Gradle Plugin: `com.android.application:9.0.1`
- Kotlin Compose Plugin: `org.jetbrains.kotlin.plugin.compose:2.0.21`
- Compile SDK: `36` (minor API `1`)
- Target SDK: `36`
- Min SDK: `24`
- Java Compatibility: `11`

### Runtime dependencies
- `androidx.core:core-ktx:1.10.1`
- `androidx.lifecycle:lifecycle-runtime-ktx:2.10.0`
- `androidx.activity:activity-compose:1.8.0`
- `androidx.compose:compose-bom:2024.09.00`
- `androidx.compose.ui:ui`
- `androidx.compose.ui:ui-graphics`
- `androidx.compose.ui:ui-tooling-preview`
- `androidx.compose.material3:material3`
- `androidx.compose.material:material-icons-extended`
- `com.google.android.material:material:1.13.0`
- `com.squareup.retrofit2:retrofit:2.11.0`
- `com.squareup.retrofit2:converter-gson:2.11.0`
- `androidx.lifecycle:lifecycle-viewmodel-compose:2.8.3`
- `androidx.datastore:datastore-preferences:1.1.1`

### Test dependencies
- Unit Test: `junit:junit:4.13.2`
- Android Test: `androidx.test.ext:junit:1.1.5`
- Android Test: `androidx.test.espresso:espresso-core:3.5.1`
- Compose Android Test:
  - `androidx.compose.ui:ui-test-junit4`
  - `androidx.compose:compose-bom:2024.09.00`

### Debug-only dependencies
- `androidx.compose.ui:ui-tooling`
- `androidx.compose.ui:ui-test-manifest`
