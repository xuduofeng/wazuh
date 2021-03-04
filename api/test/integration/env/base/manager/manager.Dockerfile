FROM public.ecr.aws/o5x5t0j3/amd64/api_development:integration_test_wazuh-generic

# INSTALL MANAGER
ARG WAZUH_BRANCH

ADD base/manager/supervisord.conf /etc/supervisor/conf.d/

RUN git clone https://github.com/wazuh/wazuh -b $WAZUH_BRANCH --depth=1
COPY base/manager/preloaded-vars.conf /wazuh/etc/preloaded-vars.conf
RUN /wazuh/install.sh

# SET CONFIGURATION FILES
COPY tools/* /tools/
COPY --chown=ossec:ossec configurations/base/manager/config/ /var/ossec/
COPY configurations/tmp/manager/ /
COPY base/manager/entrypoint.sh /scripts/entrypoint.sh

# HEALTHCHECK
HEALTHCHECK --retries=30 --interval=10s --timeout=30s --start-period=30s CMD /usr/bin/python3 /healthcheck/healthcheck.py || exit 1
