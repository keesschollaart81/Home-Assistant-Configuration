find /share/motion/backyard/*.jpg -mtime +7 -exec rm {} \;

wget -q -O /share/motion/backyard/backyard1.jpg http://$1:$2@192.168.2.11/cgi-bin/currentpic.cgi
sleep 1
wget -q -O /share/motion/backyard/backyard2.jpg http://$1:$2@192.168.2.11/cgi-bin/currentpic.cgi
sleep 1
wget -q -O /share/motion/backyard/backyard3.jpg http://$1:$2@192.168.2.11/cgi-bin/currentpic.cgi
sleep 1
wget -q -O /share/motion/backyard/backyard4.jpg http://$1:$2@192.168.2.11/cgi-bin/currentpic.cgi
sleep 1
wget -q -O /share/motion/backyard/backyard5.jpg http://$1:$2@192.168.2.11/cgi-bin/currentpic.cgi
sleep 1
wget -q -O /share/motion/backyard/backyard6.jpg http://$1:$2@192.168.2.11/cgi-bin/currentpic.cgi
sleep 1
wget -q -O /share/motion/backyard/backyard7.jpg http://$1:$2@192.168.2.11/cgi-bin/currentpic.cgi

convert -loop 0 -delay 100 /share/motion/backyard/backyard1.jpg /share/motion/backyard/backyard2.jpg /share/motion/backyard/backyard3.jpg /share/motion/backyard/backyard4.jpg /share/motion/backyard/backyard5.jpg /share/motion/backyard/backyard6.jpg /share/motion/backyard/backyard7.jpg /config/www/backyard/backyard-latest.gif

cp -a /config/www/backyard/backyard-latest.gif "/share/motion/backyard/backyard-$(date +"%m-%d-%y-%r").gif"