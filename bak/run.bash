#!/usr/bin/env bash
find . -type d -name "__pycache__" -exec rm -r {} +

echo 'fs.inotify.max_user_watches=5242880' >>/etc/sysctl.conf &&
    echo 'fs.inotify.max_user_instances=5242880' >>/etc/sysctl.conf &&
    sudo sysctl -p
