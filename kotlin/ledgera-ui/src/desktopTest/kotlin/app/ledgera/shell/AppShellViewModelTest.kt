package app.ledgera.shell

import app.ledgera.bridge.RuntimeEngine
import app.ledgera.model.EngineStatus
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertNull
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers

class AppShellViewModelTest {
    @Test
    fun startsWithNineRoadmapSectionsAndOperationsSelected() {
        val viewModel = AppShellViewModel(FakeRuntimeEngine(), CoroutineScope(Dispatchers.Unconfined))

        assertEquals(DesktopSection.Operations, viewModel.state.value.selectedSection)
        assertEquals(
            listOf(
                DesktopSection.Operations,
                DesktopSection.Reports,
                DesktopSection.Analytics,
                DesktopSection.Dashboard,
                DesktopSection.Budget,
                DesktopSection.Debts,
                DesktopSection.Distribution,
                DesktopSection.Mandatory,
                DesktopSection.Settings,
            ),
            viewModel.state.value.sections,
        )
    }

    @Test
    fun selectChangesCurrentSection() {
        val viewModel = AppShellViewModel(FakeRuntimeEngine(), CoroutineScope(Dispatchers.Unconfined))

        viewModel.select(DesktopSection.Reports)

        assertEquals(DesktopSection.Reports, viewModel.state.value.selectedSection)
    }

    @Test
    fun refreshStatusMapsEngineMessage() {
        val viewModel = AppShellViewModel(
            FakeRuntimeEngine(EngineStatus(ok = true, dbPath = "ledger.db", message = "ready")),
            CoroutineScope(Dispatchers.Unconfined),
        )

        viewModel.refreshStatus()

        assertEquals("ready", viewModel.state.value.engineMessage)
        assertNull(viewModel.state.value.error)
    }

    @Test
    fun refreshStatusMapsEngineFailure() {
        val viewModel = AppShellViewModel(FailingRuntimeEngine(), CoroutineScope(Dispatchers.Unconfined))

        viewModel.refreshStatus()

        assertEquals("Engine unavailable", viewModel.state.value.engineMessage)
        assertEquals("boom", viewModel.state.value.error)
    }
}

private class FakeRuntimeEngine(
    private val status: EngineStatus = EngineStatus(ok = true, dbPath = "ledger.db", message = "ready"),
) : RuntimeEngine {
    override suspend fun status(): EngineStatus = status
}

private class FailingRuntimeEngine : RuntimeEngine {
    override suspend fun status(): EngineStatus = error("boom")
}
