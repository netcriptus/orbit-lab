set -e

omf tell -a offh -t all
omf load -i baseline.ndz -t all
omf tell -a on -t all

echo -e "We are now good to go\n"