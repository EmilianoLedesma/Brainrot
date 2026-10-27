import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {Coffee,COFFEE_FRAMES} from './Coffee';
import {CoffeeLight,COFFEE_LIGHT_FRAMES} from './CoffeeLight';
registerRoot(()=><><Composition id="Coffee" component={Coffee} width={1080} height={1920} fps={30} durationInFrames={COFFEE_FRAMES}/><Composition id="CoffeeLight" component={CoffeeLight} width={1080} height={1920} fps={30} durationInFrames={COFFEE_LIGHT_FRAMES}/></>);
