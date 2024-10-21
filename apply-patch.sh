#!/bin/bash
# usage ./apply-patch.sh <zip-file> <round-name>

zip_path="$(realpath $1)"

# round-n
git clone -b base git@github.com:gctf-kijitora/round.git tmp
cd tmp
unzip -o ${zip_path}
git switch -c $2
git add .
git commit -a -m "add game"
git push origin $2
cd ..
rm -rf tmp

# round-n-modded
mv requirements.txt requirements-mod.txt
mv game/engine/shaders/shapelayer_f.glsl game/engine/shaders/shapelayer_f.glsl.bak
unzip -o ${zip_path}
mv game/engine/shaders/shapelayer_f.glsl.bak game/engine/shaders/shapelayer_f.glsl

git switch -c $2-modded
git add .
git commit -a -m "add modded game"
git push origin $2-modded
git branch --set-upstream-to=origin/$2-modded $2-modded
