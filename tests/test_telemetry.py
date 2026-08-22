import importlib


def test_setup_telemetry_is_noop_without_connection_string(monkeypatch):
	# Without the connection string, setup must not touch the Azure SDK
	# at all — local dev and CI stay telemetry-free.
	monkeypatch.delenv('APPLICATIONINSIGHTS_CONNECTION_STRING', raising=False)
	telemetry = importlib.import_module('app.core.telemetry')
	assert telemetry.setup_telemetry() is None


def test_setup_telemetry_configures_azure_monitor_when_configured(monkeypatch):
	# With the connection string present, the exporter starts. The real
	# configure_azure_monitor is swapped for a stub so the test never
	# talks to Azure; we only assert our wiring calls it.
	calls = []

	def fake_configure(**kwargs):
		calls.append(kwargs)

	monkeypatch.setenv(
		'APPLICATIONINSIGHTS_CONNECTION_STRING',
		'InstrumentationKey=00000000-0000-0000-0000-000000000000',
	)
	monkeypatch.setattr(
		'azure.monitor.opentelemetry.configure_azure_monitor',
		fake_configure,
		raising=False,
	)
	telemetry = importlib.import_module('app.core.telemetry')
	telemetry.setup_telemetry()
	assert len(calls) == 1


def test_app_starts_cleanly_with_telemetry_enabled(monkeypatch):
	# The paranoid test: with the env var set (as in production), the
	# import chain — telemetry wiring included — must still build the app
	# without crashing. The exporter is stubbed to avoid network I/O.
	monkeypatch.setenv(
		'APPLICATIONINSIGHTS_CONNECTION_STRING',
		'InstrumentationKey=00000000-0000-0000-0000-000000000000',
	)
	monkeypatch.setattr(
		'azure.monitor.opentelemetry.configure_azure_monitor',
		lambda **kwargs: None,
		raising=False,
	)
	# main.py was already imported at collection time (by other tests)
	# when the env var was absent — so reload it with the var present.
	importlib.sys.modules.pop('app.main', None)
	main = importlib.import_module('app.main')
	assert main.app.title  # app exists and was built after telemetry wiring
