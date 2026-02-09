#!/bin/sh

PREFIX="/usr/local"

install -t "$PREFIX/bin" phwmon.py
install -t "$PREFIX/share/applications" phwmon.desktop
