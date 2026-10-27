import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {ZebraStripes,ZEBRA_STRIPES_FRAMES} from './ZebraStripes';
registerRoot(()=><Composition id="ZebraStripes" component={ZebraStripes} width={1080} height={1920} fps={30} durationInFrames={ZEBRA_STRIPES_FRAMES}/>);
