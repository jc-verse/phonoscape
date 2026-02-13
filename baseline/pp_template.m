function ppState = pp_template(ppState, action, varargin)
%PP_TEMPLATE  - MVIEW plotting procedure
%
% This is an example MVIEW plotting procedure, which just mimics default spatial plotting behavior
%
% Clone & tailor this file to create new plotting procedures.
%
% User labelling procedures must supply four handlers:
%	CLOSE   - delete the plotting window
%	INIT    - initialize the plotting window
%	UDBNDS  - update the plot based on current selection
%	UDCURS  - update the plot based on current cursor location
%
% Plotting procedures may store internal state information in a variable which is
% passed as the first argument supplied to each handler

% mkt 05/08
% mkt 05/18 graphics updates

%	branch by action (2nd argument)

switch upper(action),
		
%-----------------------------------------------------------------------------
% CLOSE:  delete plot

	case 'CLOSE',
		fh = ppState.FH;
		if ishandle(fh), delete(fh); end;
		
	
%-----------------------------------------------------------------------------
% INIT:  initialize plot
%
%	ppState set to mview state copy
%	varargin{1} trajectories to plot (default all)
%	varargin{2} view (default [34 14])
%
% 	returns updated ppState

	case 'INIT',
		fh = figure('name','SPATIAL PLOT', ...
					'numberTitle', 'off', ...
					'tag', 'MVIEW');
					
% keep figure on top
		drawnow;
		if usejava('jvm'),			
			ws = warning('off','MATLAB:HandleGraphics:ObsoletedProperty:JavaFrame');
			jf = get(handle(fh),'JavaFrame');
			warning(ws.state,'MATLAB:HandleGraphics:ObsoletedProperty:JavaFrame');
			jf.fHG2Client.getWindow.setAlwaysOnTop(true);
		end;
		
% find range
		data = ppState.DATA;
		names = {data.NAME};
		pal = ppState.PALATE;
		if length(varargin) < 1 || isempty(varargin{1}),
			traj = names;
			for k = length(traj) : -1 : 1,
				if size(data(k).SIGNAL,2) < 3, traj(k) = []; end;
			end;
		else,
			traj = upper(varargin{1});
		end;
		if length(varargin) < 2, vue = [34 14]; else, vue = varargin{2}; end;
		for k = 1 : length(traj),
			tIdx(k) = strmatch(traj{k},names,'exact');
			rMin(k,:) = min(data(tIdx(k)).SIGNAL(:,1:3));
			rMax(k,:) = max(data(tIdx(k)).SIGNAL(:,1:3));
		end;
		if ~isempty(pal),
			rMin(k+1,:) = min(pal);
			rMax(k+1,:) = max(pal);
		end;
		rMin = min(rMin);
		rMax = max(rMax);
		spread = 1.1*max(rMax - rMin) / 2;
		r = [rMax-rMin]/2+rMin;
		
% init axis
		set(gca, 'xlim',spread*[-1 1]+r(1), 'ylim',spread*[-1 1]+r(2), 'zlim',spread*[-1 1]+r(3), ...
				'box', 'on');
		axis equal;
		if ~isempty(pal),
			line(pal(:,1),pal(:,2),pal(:,3),'color',[.6 .6 .6]);
		end;
		
% plot current position
		for k = 1 : length(traj),
			sr = data(tIdx(k)).SRATE;
			s = ppState.CURSOR*sr/1000;
			s1 = floor(s) + 1;
			s2 = s1 + 1;
			tMax = size(data(tIdx(k)).SIGNAL,1);
			if s2 > tMax, s2 = tMax; end;
			v = data(tIdx(k)).SIGNAL(s1:s2,1:3);
			d = v(1,:) + diff(v) * (s-s1);		% linear interpolation
			lh(k) = line(d(1),d(2),d(3),'marker','.','markersize',20,'color','b');
		end;
		view(vue);
		
% save data
		ppState = struct('FH',fh, 'LH',lh, 'TIDX',tIdx, 'MVIEW',ppState.FH);
		
		
%-----------------------------------------------------------------------------
% UDBNDS:  update the plot based on current selection
%
%	varargin{1} set to state.HEAD
%	varargin{2} set to state.TAIL

	case 'UDBNDS',
		disp('updated selection for pp_template');
	
%-----------------------------------------------------------------------------
% UDCURS:  update the plot based on current cursor location
%
%	varargin{1} set to state.CURSOR

	case 'UDCURS',
		if ~ishandle(ppState.FH), return; end;
		c = varargin{1};
		state = get(ppState.MVIEW,'userData');
		tIdx = ppState.TIDX;
		lh = ppState.LH;
		for k = 1 : length(tIdx),
			sr = state.DATA(tIdx(k)).SRATE;
			s = c*sr/1000;
			s1 = floor(s) + 1;
			s2 = s1 + 1;
			tMax = size(state.DATA(tIdx(k)).SIGNAL,1);
			if s2 > tMax, s2 = tMax; end;
			v = state.DATA(tIdx(k)).SIGNAL(s1:s2,1:3);
			d = v(1,:) + diff(v) * (s-s1);		% linear interpolation
			set(lh(k),'xdata',d(1),'ydata',d(2),'zdata',d(3));
		end;

%-----------------------------------------------------------------------------
% error

	otherwise,
		error(['PP_TEMPLATE:  unrecognized action (', action, ')']);
	
end;



