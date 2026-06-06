package app.ledgera

import java.net.ServerSocket
import java.nio.file.Files
import kotlin.test.Test
import kotlin.test.assertNull
import kotlin.test.assertTrue

class SingleInstanceSupportTest {
    @Test
    fun secondAcquireReturnsNullWhileFirstInstanceOwnsLock() {
        val lockPath = Files.createTempDirectory("ledgera-single-instance-test")
            .resolve("app.lock")
        val port = freeLoopbackPort()

        SingleInstanceSupport.acquire(lockPath, port, onActivate = {})!!.use {
            assertNull(SingleInstanceSupport.acquire(lockPath, freeLoopbackPort(), onActivate = {}))
        }

        SingleInstanceSupport.acquire(lockPath, port, onActivate = {})!!.close()
    }

    @Test
    fun activationRequestNotifiesRunningInstance() {
        val port = freeLoopbackPort()
        val activated = java.util.concurrent.CountDownLatch(1)
        val server = ActivationServer(port) {
            activated.countDown()
        }

        server.use {
            it.start()
            SingleInstanceSupport.requestActivation(port)

            assertTrue(activated.await(2, java.util.concurrent.TimeUnit.SECONDS))
        }
    }
}

private fun freeLoopbackPort(): Int =
    ServerSocket(0).use { it.localPort }
