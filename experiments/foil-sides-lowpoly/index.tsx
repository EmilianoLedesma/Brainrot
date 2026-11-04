import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {FoilSides,FOIL_FRAMES} from './FoilSides';
registerRoot(()=><Composition id="FoilSides" component={FoilSides} width={1080} height={1920} fps={30} durationInFrames={FOIL_FRAMES}/>);
