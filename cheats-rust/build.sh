#/bin/bash
rm -rf target build/*
cd search
rustup override set nightly
maturin build --profile opt -i $(which python3)
cd ../

# do not execute command here because you may need to use different command in some environment like `uv pip`
echo run: pip install target/wheels/*
