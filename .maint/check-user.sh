#!/bin/bash

MIGAS_PATH=$(realpath $(dirname $(dirname $0)))
python -m pip install -U $MIGAS_PATH &> /dev/null
python -c "import migas; migas.setup(); print(f'Generated user id: {migas.config.Config.user_id}')"
