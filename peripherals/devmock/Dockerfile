FROM wiremock/wiremock:3.13.2

# State extension: lets a mapping branch on state keyed by the task id, which is
# what ends the re-delivery loop once the SDK reports a final task. Dropped on the
# classpath, so WireMock loads it without an --extensions flag.
ARG STATE_EXTENSION_VERSION=0.10.1
ADD --chmod=644 \
    https://repo1.maven.org/maven2/org/wiremock/extensions/wiremock-state-extension-standalone/${STATE_EXTENSION_VERSION}/wiremock-state-extension-standalone-${STATE_EXTENSION_VERSION}.jar \
    /var/wiremock/extensions/
