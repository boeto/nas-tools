FROM alpine:3.17 AS Builder
COPY --chmod=755 package_list.txt /app/package_list.txt
COPY --chmod=755 requirements.txt /app/requirements.txt
RUN apk add --no-cache --virtual .build-deps \
    libffi-dev \
    gcc \
    musl-dev \
    libxml2-dev \
    libxslt-dev \
    && apk add --no-cache $(cat /app/package_list.txt) \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && curl https://rclone.org/install.sh | bash \
    && if [ "$(uname -m)" = "x86_64" ]; then ARCH=amd64; elif [ "$(uname -m)" = "aarch64" ]; then ARCH=arm64; fi \
    && curl https://dl.min.io/client/mc/release/linux-${ARCH}/mc --create-dirs -o /usr/bin/mc \
    && chmod +x /usr/bin/mc \
    && pip install --upgrade pip setuptools wheel \
    && pip install cython \
    && pip install -r /app/requirements.txt \
    && apk del --purge .build-deps \
    && rm -rf /tmp/* /root/.cache /var/cache/apk/* \
    /app/package_list.txt /app/requirements.txt
COPY --chmod=755 ./rootfs /
FROM scratch AS APP
COPY --from=Builder / /
ENV S6_SERVICES_GRACETIME=30000 \
    S6_KILL_GRACETIME=60000 \
    S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0 \
    S6_SYNC_DISKS=1 \
    HOME="/nt" \
    TERM="xterm" \
    PATH=${PATH}:/usr/lib/chromium \
    LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    NASTOOL_CONFIG="/config/config.yaml" \
    NASTOOL_AUTO_UPDATE=true \
    NASTOOL_CN_UPDATE=true \
    NASTOOL_VERSION=master \
    PS1="\u@\h:\w \$ " \
    REPO_URL="https://github.com/boeto/nas-tools.git" \
    PYPI_MIRROR="https://pypi.tuna.tsinghua.edu.cn/simple" \
    ALPINE_MIRROR="mirrors.ustc.edu.cn" \
    PUID=0 \
    PGID=0 \
    UMASK=000 \
    WORKDIR="/nas-tools"
WORKDIR ${WORKDIR}
COPY --chmod=755 *.py *.txt ./
COPY --chmod=755 app/ ./app/
COPY --chmod=755 web/ ./web/
COPY --chmod=755 scripts/ ./scripts/
COPY --chmod=755 config/ ./config/
COPY --chmod=755 third_party/ ./third_party/
COPY --chmod=755 docker/entrypoint.sh ./docker/
RUN mkdir ${HOME} \
    && addgroup -S nt -g 911 \
    && adduser -S nt -G nt -h ${HOME} -s /bin/bash -u 911 \
    && python_ver=$(python3 -V | awk '{print $2}') \
    && echo "${WORKDIR}/" > /usr/lib/python${python_ver%.*}/site-packages/nas-tools.pth \
    && echo 'fs.inotify.max_user_watches=5242880' >> /etc/sysctl.conf \
    && echo 'fs.inotify.max_user_instances=5242880' >> /etc/sysctl.conf \
    && echo "nt ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers \
    && git config --global pull.ff only \
    # && git clone -b master ${REPO_URL} ${WORKDIR} --depth=1 --recurse-submodule \
    && git config --global --add safe.directory ${WORKDIR}
# && chmod +x /nas-tools/docker/entrypoint.sh
EXPOSE 3000
VOLUME ["/config"]
ENTRYPOINT [ "/init" ]
