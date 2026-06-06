package app.ledgera

import java.awt.Frame
import java.awt.Window
import java.io.Closeable
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.ServerSocket
import java.net.Socket
import java.nio.channels.FileChannel
import java.nio.channels.FileLock
import java.nio.file.Files
import java.nio.file.Path
import java.nio.file.StandardOpenOption
import javax.swing.SwingUtilities
import kotlin.concurrent.thread

private const val LOCK_FILE_NAME = "ledgera-desktop.lock"
private const val ACTIVATION_PORT = 47321
private const val ACTIVATION_TOKEN = "LEDGERA_ACTIVATE"

internal object SingleInstanceSupport {
    fun acquire(
        lockPath: Path = defaultLockPath(),
        activationPort: Int = ACTIVATION_PORT,
        onActivate: () -> Unit = ::bringApplicationToFront,
    ): SingleInstanceHandle? {
        Files.createDirectories(lockPath.parent)
        val channel = FileChannel.open(
            lockPath,
            StandardOpenOption.CREATE,
            StandardOpenOption.WRITE,
        )
        val lock = channel.tryLockOrNull()
        if (lock == null) {
            channel.close()
            return null
        }

        val server = ActivationServer(activationPort, onActivate)
        runCatching { server.start() }.onFailure {
            lock.release()
            channel.close()
            throw it
        }
        return SingleInstanceHandle(lock, channel, server)
    }

    fun requestActivation(port: Int = ACTIVATION_PORT) {
        runCatching {
            Socket().use { socket ->
                socket.connect(InetSocketAddress(InetAddress.getLoopbackAddress(), port), 250)
                socket.getOutputStream().write(ACTIVATION_TOKEN.toByteArray(Charsets.UTF_8))
                socket.getOutputStream().flush()
            }
        }
    }

    private fun defaultLockPath(): Path =
        Path.of(System.getProperty("java.io.tmpdir"), LOCK_FILE_NAME)
}

internal class SingleInstanceHandle(
    private val lock: FileLock,
    private val channel: FileChannel,
    private val activationServer: ActivationServer,
) : Closeable {
    override fun close() {
        activationServer.close()
        lock.release()
        channel.close()
    }
}

internal class ActivationServer(
    private val port: Int,
    private val onActivate: () -> Unit,
) : Closeable {
    private var serverSocket: ServerSocket? = null
    private var serverThread: Thread? = null

    fun start() {
        val socket = ServerSocket()
        socket.reuseAddress = true
        socket.bind(InetSocketAddress(InetAddress.getLoopbackAddress(), port))
        serverSocket = socket
        serverThread = thread(
            start = true,
            isDaemon = true,
            name = "ledgera-single-instance-activation",
        ) {
            listen(socket)
        }
    }

    private fun listen(socket: ServerSocket) {
        while (!socket.isClosed) {
            val client = runCatching { socket.accept() }.getOrNull() ?: break
            client.use {
                val payload = it.getInputStream().readNBytes(ACTIVATION_TOKEN.length)
                    .toString(Charsets.UTF_8)
                if (payload == ACTIVATION_TOKEN) {
                    onActivate()
                }
            }
        }
    }

    override fun close() {
        serverSocket?.close()
        serverThread?.join(500)
    }
}

private fun FileChannel.tryLockOrNull(): FileLock? =
    runCatching { tryLock() }.getOrNull()

private fun bringApplicationToFront() {
    SwingUtilities.invokeLater {
        Window.getWindows()
            .filter { it.isDisplayable }
            .forEach { window ->
                if (window is Frame && window.extendedState and Frame.ICONIFIED != 0) {
                    window.extendedState = window.extendedState and Frame.ICONIFIED.inv()
                }
                window.isVisible = true
                window.toFront()
                window.requestFocus()
            }
    }
}
