#!/bin/bash

chmod 700 ~/.ssh
find ~/.ssh -type f -name "*.pub" -exec chmod 644 {} \;
cd ~/.ssh
chmod 600 comp_jk id_ed25519 id_rsa_comp id_rsa_voc ty_key xiyuanyang_rsa
chmod 644 config
cd -

ls -la ~/.ssh