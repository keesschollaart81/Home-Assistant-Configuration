convert -loop 0 -delay 100 /share/motion/front-door/front1.jpg /share/motion/front-door/front2.jpg /share/motion/front-door/front3.jpg /share/motion/front-door/front4.jpg /share/motion/front-door/front5.jpg /share/motion/front-door/front6.jpg /share/motion/front-door/front7.jpg /share/motion/front-door/front8.jpg /share/motion/front-door/front9.jpg /share/motion/front-door/front-door-latest.gif 

convert /share/motion/front-door/front-door-latest.gif -fuzz 15% -layers Optimize  /share/motion/front-door/front-door-latest-small.gif

cp -a /share/motion/front-door/front-door-latest-small.gif "/share/motion/front-door/front-door-$(date +"%m-%d-%y-%r").gif"
