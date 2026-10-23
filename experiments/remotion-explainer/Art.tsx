import React from 'react';

const ink = '#182c36';
const Canvas: React.FC<React.PropsWithChildren> = ({children}) => <svg width="100%" height="100%" viewBox="0 0 500 500" fill="none" xmlns="http://www.w3.org/2000/svg">{children}</svg>;

export const Spoon: React.FC<{wood?: boolean}> = ({wood=false}) => <Canvas>
  <g transform="rotate(-28 250 250)" stroke={ink} strokeWidth="9" strokeLinejoin="round">
    <path d="M225 233 C158 212 154 97 200 57 C230 30 279 31 304 61 C347 109 330 209 276 234 L284 425 Q285 461 251 461 Q219 461 221 427Z" fill={wood?'#d69b50':'#9bbdc9'}/>
    <path d="M229 214 C190 194 188 109 215 80 C235 60 268 59 289 83 C314 114 305 191 273 211Z" fill={wood?'#f1c47b':'#d9eaf0'} strokeWidth="5"/>
    <path d="M242 261 L240 418 Q242 438 256 438" stroke={wood?'#f7d99a':'#eafbff'} strokeWidth="10" strokeLinecap="round"/>
    {wood ? <g stroke="#a96e35" strokeWidth="4" strokeLinecap="round"><path d="M235 84 Q206 128 230 186 M256 77 Q232 128 255 196 M279 95 Q264 126 276 174 M259 274 L261 400"/><ellipse cx="251" cy="357" rx="7" ry="20"/></g> : <><path d="M212 119 Q205 155 224 182" stroke="#fff" strokeWidth="12" strokeLinecap="round"/><path d="M288 84 Q310 132 283 188" stroke="#769ba9" strokeWidth="9" strokeLinecap="round"/></>}
  </g>
</Canvas>;

export const Hand: React.FC = () => <Canvas>
  <path d="M154 476 L163 359 Q132 325 112 291 L66 222 Q50 194 70 179 Q91 165 111 188 L157 236 L114 100 Q107 72 130 64 Q154 58 164 85 L203 193 L185 59 Q182 30 207 28 Q232 27 237 57 L258 184 L266 65 Q268 38 292 42 Q315 46 312 72 L306 205 L333 122 Q343 95 366 107 Q385 118 376 143 L341 280 Q390 223 417 231 Q449 244 422 276 L378 333 Q365 375 328 397 L330 476Z" fill="#ee8b76" stroke={ink} strokeWidth="9" strokeLinejoin="round"/>
  <path d="M177 270 Q234 229 290 262 Q318 280 304 320 M186 339 Q216 313 243 323 M328 287 Q296 320 310 354" stroke="#bc5a51" strokeWidth="7" strokeLinecap="round"/>
  <path d="M192 384 Q251 419 307 389 L309 465 L177 465Z" fill="#d86e61"/>
  <path d="M120 209 L147 246 M206 86 L218 175 M286 85 L280 178" stroke="#ffc3a7" strokeWidth="10" strokeLinecap="round"/>
</Canvas>;

export const Ice: React.FC<{melt?:number}> = ({melt=0}) => {
  const m=Math.min(1,Math.max(0,melt));
  return <Canvas><ellipse cx="250" cy="393" rx={130+m*83} ry={23+m*17} fill="#76c6e4" opacity={0.3+m*0.4}/>
    <g transform={`translate(${m*65} ${m*165}) scale(${1-m*0.26} ${1-m*0.48})`} stroke={ink} strokeWidth="8" strokeLinejoin="round">
      <path d="M113 170 L246 99 L385 166 L376 331 L243 406 L115 333Z" fill="#91dcf0"/>
      <path d="M113 170 L247 239 L385 166 L246 99Z" fill="#d1f6ff"/>
      <path d="M247 239 L243 406 L376 331 L385 166Z" fill="#55b9de"/>
      <path d="M113 170 L247 239 L243 406 M247 239 L385 166"/>
      <path d="M139 190 L139 308 L177 332 M174 159 L245 125 L297 150 M272 270 L270 352" stroke="#f3fdff" strokeWidth="13" strokeLinecap="round"/>
      <path d="M202 230 L186 265 L210 287 M333 221 L316 257 L335 275" stroke="#2f99c3" strokeWidth="4"/>
    </g>
    {m>0.15 && <path d="M397 330 Q378 359 379 370 A18 18 0 0 0 415 370 Q415 357 397 330Z" fill="#69c8e6" stroke={ink} strokeWidth="5"/>}
  </Canvas>;
};

export const Block: React.FC<{wood?:boolean;heat?:number}> = ({wood=false,heat=0}) => <Canvas>
  <g stroke={ink} strokeWidth="8" strokeLinejoin="round">
    <path d="M47 162 L315 98 L455 176 L191 248Z" fill={wood?'#f0c282':'#d9e9e9'}/>
    <path d="M47 162 L191 248 L191 398 L47 308Z" fill={wood?'#a96e38':'#739dab'}/>
    <path d="M191 248 L455 176 L455 324 L191 398Z" fill={wood?'#d49a53':'#a5c9d1'}/>
  </g>
  {wood ? <g stroke="#9e632e" strokeWidth="4" opacity=".7"><path d="M70 164 Q190 164 330 126 M105 186 Q229 179 366 146 M151 213 Q265 205 414 167 M211 276 Q341 262 435 213 M210 308 Q344 287 435 248 M211 349 Q328 319 435 286"/><ellipse cx="316" cy="286" rx="27" ry="10" transform="rotate(-15 316 286)"/></g> : <g stroke="#efffff" strokeWidth="9" strokeLinecap="round"><path d="M78 168 L191 222 L337 183 M215 270 L426 214 M214 370 L274 353"/></g>}
  {heat>0 && <g fill="#e7734b" opacity={Math.min(1,heat)}>{[0,1,2,3,4].map(i=><circle key={i} cx={110+i*65} cy={178+(i%2)*17} r="13"/>)}</g>}
</Canvas>;

export const Thermometer: React.FC<{value?:number;hot?:boolean}> = ({value=22,hot=false}) => <Canvas>
  <path d="M209 323 L209 83 A41 41 0 0 1 291 83 L291 323 A79 79 0 1 1 209 323Z" fill="#f6efe2" stroke={ink} strokeWidth="10"/>
  <path d="M250 351 L250 104" stroke="#d6d7d0" strokeWidth="25" strokeLinecap="round"/>
  <path d={`M250 351 L250 ${Math.max(104,Math.min(325,325-value*2.3))}`} stroke={hot?'#ea6545':'#52b4d0'} strokeWidth="25" strokeLinecap="round"/>
  <circle cx="250" cy="387" r="49" fill={hot?'#ea6545':'#52b4d0'}/>
  <path d="M220 389 Q217 366 238 357" stroke="#fff" strokeWidth="9" strokeLinecap="round" opacity=".65"/>
  {[112,151,190,229,268,307].map((y,i)=><path key={y} d={`M299 ${y} h${i%2?22:35}`} stroke={ink} strokeWidth="6" strokeLinecap="round"/>)}
  <text x="355" y="396" textAnchor="middle" fontFamily="DM Sans" fontWeight="800" fontSize="37" fill={ink}>{value}°</text>
</Canvas>;

