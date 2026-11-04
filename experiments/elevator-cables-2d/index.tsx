import React from 'react';
import {registerRoot,Composition} from 'remotion';
import {ElevatorCables,ELEVATOR_FRAMES} from './ElevatorCables';
registerRoot(()=><Composition id="ElevatorCables" component={ElevatorCables} width={1080} height={1920} fps={30} durationInFrames={ELEVATOR_FRAMES}/>);
