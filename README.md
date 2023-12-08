
# NAS媒体库管理工具

![logo-blue](https://user-images.githubusercontent.com/51039935/197520391-f35db354-6071-4c12-86ea-fc450f04bc85.png)

[![GitHub stars](https://img.shields.io/github/stars/boeto/nas-tools?style=plastic)](https://github.com/boeto/nas-tools/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/boeto/nas-tools?style=plastic)](https://github.com/boeto/nas-tools/network/members)
[![GitHub issues](https://img.shields.io/github/issues/boeto/nas-tools?style=plastic)](https://github.com/boeto/nas-tools/issues)
[![GitHub license](https://img.shields.io/github/license/boeto/nas-tools?style=plastic)](https://github.com/boeto/nas-tools/blob/master/LICENSE.md)
[![Docker pulls](https://img.shields.io/docker/pulls/boeto/nas-tools?style=plastic)](https://hub.docker.com/r/boeto/nas-tools)
[![Platform](https://img.shields.io/badge/platform-amd64/arm64-pink?style=plastic)](https://hub.docker.com/r/boeto/nas-tools)

Docker：

* <https://hub.docker.com/r/boeto/nas-tools>
* <https://hub.docker.com/r/boeto/nas-tools>

TG频道：<https://t.me/nastool_official>

Wiki：<https://wiki.nastool.org>

API: <http://localhost:3000/api/v1/>

## 功能

NAS媒体库管理工具。

## 安装

### 1、Docker

```bash
docker pull boeto/nas-tools:latest
```

教程见 [这里](docker/readme.md) 。

如无法连接Github，将NASTOOL_CN_UPDATE设置为true可使用国内源加速安装依赖。

### 2、本地运行

python3.10版本，需要预安装cython，如发现缺少依赖包需额外安装：

```bash
git clone -b master https://github.com/boeto/nas-tools --recurse-submodule
cd nas-tools
python3 -m pip install -r requirements.txt
export NASTOOL_CONFIG="/xxx/config/config.yaml"
nohup python3 run.py &
```

## 开发

### 使用 poetry 配置开发环境

* [安装 poetry](https://python-poetry.org/docs/#installation)

* 安装依赖和开发套件

```bash
git clone --single-branch -b dev https://github.com/boeto/nas-tools --recurse-submodule
cd nas-tools

# 切换python版本到3.10
# poetry env use "${HOME}/.pyenv/versions/3.10.13/bin/python3"

# 安装依赖
poetry install --no-root

# 初始化 pre-commit
poetry run pre-commit install --install-hooks
poetry run pre-commit autoupdate
```

* 运行程序

```bash
# 配置运行env
tee .env <<EOF
NASTOOL_CONFIG=config-dev/config.yaml
FLASK_DEBUG=1
EOF

#启动app
poetry run python3 run.py
```

* 测试

编写测试代码，并通过测试。测试工具：[pytest](https://docs.pytest.org/)

```bash
pytest -s -v tests
```

* 格式化代码并提交更改

```bash
git add <files>
poetry shell
cz commit
git push
```

## 免责声明

1) 本软件仅供学习交流使用，软件本身不提供任何内容，仅作为辅助工具简化用户手工操作，对用户的行为及内容毫不知情，使用本软件产生的任何责任需由使用者本人承担。
2) 本软件代码开源，基于开源代码进行修改，人为去除相关限制导致软件被分发、传播并造成责任事件的，需由代码修改发布者承担全部责任。本项目的用户认证机制是项目长期生存下去的基础，建议不要修改用户认证并公开发布。
3) 本项目没有在任何地方发布捐赠信息页面，也不会接受捐赠或进行收费，请仔细辨别避免误导。
4) 此repo在原作者的基础上进行修改，感谢nas-tools的开发团队。
