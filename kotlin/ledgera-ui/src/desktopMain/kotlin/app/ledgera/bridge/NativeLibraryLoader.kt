package app.ledgera.bridge

import java.nio.file.Files
import kotlin.io.path.outputStream

object NativeLibraryLoader {
    private var loaded = false

    @Synchronized
    fun ensureAvailable() {
        if (loaded) {
            return
        }
        val resourceName = when {
            System.getProperty("os.name").lowercase().contains("win") -> "ledgera_engine.dll"
            System.getProperty("os.name").lowercase().contains("mac") -> "libledgera_engine.dylib"
            else -> "libledgera_engine.so"
        }
        val resourcePath = "/native/$resourceName"
        val input = NativeLibraryLoader::class.java.getResourceAsStream(resourcePath)
            ?: error("Native Rust library not found in resources: $resourcePath")
        val targetDir = Files.createTempDirectory("ledgera-engine-native")
        val target = targetDir.resolve(resourceName)
        input.use { source ->
            target.outputStream().use { destination -> source.copyTo(destination) }
        }
        System.setProperty(
            "jna.library.path",
            listOf(targetDir.toAbsolutePath().toString(), System.getProperty("jna.library.path", ""))
                .filter { it.isNotBlank() }
                .joinToString(System.getProperty("path.separator")),
        )
        Files.deleteIfExists(targetDir.resolve(".probe"))
        loaded = true
    }
}
