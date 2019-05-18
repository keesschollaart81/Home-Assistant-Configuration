wget -q -O /share/motion/front-door/front1.jpg http://192.168.2.22/jpg
sleep 1
wget -q -O /share/motion/front-door/front2.jpg http://192.168.2.22/jpg
sleep 1
wget -q -O /share/motion/front-door/front3.jpg http://192.168.2.22/jpg
sleep 1
wget -q -O /share/motion/front-door/front4.jpg http://192.168.2.22/jpg
sleep 1
wget -q -O /share/motion/front-door/front5.jpg http://192.168.2.22/jpg
sleep 1
wget -q -O /share/motion/front-door/front6.jpg http://192.168.2.22/jpg
sleep 1
wget -q -O /share/motion/front-door/front7.jpg http://192.168.2.22/jpg

convert -loop 0 -delay 100 /share/motion/front-door/front1.jpg /share/motion/front-door/front2.jpg /share/motion/front-door/front3.jpg /share/motion/front-door/front4.jpg /share/motion/front-door/front5.jpg /share/motion/front-door/front6.jpg /share/motion/front-door/front7.jpg /config/www/front-door/front-door-latest.gif

cp -a /config/www/front-door/front-door-latest.gif "/share/motion/front-door/front-door-$(date +"%m-%d-%y-%r").gif"

find /share/motion/front-door/*.* -mtime +4 -exec rm {} \;