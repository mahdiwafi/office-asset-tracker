# Telemetry wiring for Application Insights.
#
# Configured entirely by the environment, like every other knob in this
# service: with APPLICATIONINSIGHTS_CONNECTION_STRING set (the container
# app in Azure), OpenTelemetry exports traces, metrics and logs to App
# Insights; without it (local dev, CI, tests) this is a no-op. There is
# no separate 'telemetry on' flag to forget to set — presence of the
# secret IS the flag, so the code path exercised locally is the same one
# exercised in production.
import os


def setup_telemetry() -> None:
	"""Start the Azure Monitor exporter when configured; no-op otherwise."""
	if not os.environ.get('APPLICATIONINSIGHTS_CONNECTION_STRING'):
		return
	# Imported lazily so the heavy OpenTelemetry machinery never loads in
	# environments without telemetry, keeping test startup and CI fast.
	from azure.monitor.opentelemetry import configure_azure_monitor

	configure_azure_monitor()
