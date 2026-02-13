function mOut = mview(varargin)
%MVIEW  - multiple concurrently recorded data streams viewer
%
%	usage:  mview data
%	        mview(data)
%	        mview(data, params)
%	        mview abort		% close all MVIEW viewers
%
% where DATA is one of
%	MAVIS-compatible array-of-structs
%	string evaluating to a (possibly wild-carded) variable name
%	cell string array of variable names
%	  (if variables not found in workspace loaded from mat files on path)
%
% the expected array-of-structs format should minimally include fields
%	'NAME'  - trajectory name; e.g. 'AUDIO'
%	'SRATE' - sampling rate (Hz)
%	'SIGNAL'- trajectory data [nSamps x nDims]
%
% and PARAMS is one of the following NAME, VALUE pairs:
%	CONFIG  - specify a previously saved configuration variable
%	DPROC   - specify user procedure(s) that precompute derived data
%	FTRAJ   - framing trajectory (default 1)
%	HEAD    - offset into data for display (msecs; default 0)
%	LABELS  - specify a set of previously defined labels
%	LPROC   - specify a user labelling procedure
%	IS3D    - override test for 3rd dimension (0|1)
%	MAP     - gives ordering of displayed signals in temporal display
%	            modifiers:  (v|a)<TRAJECTORY_ID>(x)(y)(z) <SIGNAL_ID>_(SPECT|F0|RMS|ZC|VEL)
%	PALATE  - specify a [nPoints x X,Y(,Z)] palate trace
%	PHARYNX - specify a [2 x X,Y] pharynx line
%	PPROC   - specify user plotting procedure(s)
%	SEX     - specify subject gender ({'M'}|'F'; affects F0 heuristics)
%	SPLINE  - specify indices of trajectories to connect by spline (positive)
%	            or straight lines (negative)
%	            [] connects all T* trajectories, 0 disables (default)
%	SPREAD  - specify audio signal scaling (use 'AUTO' for self-normalization)
%	TAIL    - end of displayed data offset (msecs; default full duration)
%	SPATEX  - signals to exclude from spatial display (default all multidimensional)
%	VIEW    - set spatial view (default [27 20])
%
% Currently available LPROCS:
%	LP_SNAPEX, LP_EXTENTS, LP_FINDGEST
% Currently available DPROCs:
%	MDP_LIPAPERTURE, MDP_PALDIST, MDP_STRIPREF
% Currently available PPROCS:
%	PP_PHASE, PP_ANGLES
% Multiple LPROCs, DPROCs or PPROCs may be specified as a cellstring array
%
% e.g. display DATA with PALate, SPECTrogram, TT vertical movement & velocity
%	mview(data, 'PALATE', pal, 'MAP', {'AUDIO_SPECT', 'TTy', 'vTTy'})
%
% display first variable matching FOO* displaying entire token with no connecting lines
%	mview('FOO*','TAIL',0,'SPLINE',0)
%
% compute lip aperture and distance-to-palate, use lp_snapex for labeling
%	mview('FOO*','DPROC',{'mdp_LipAperture','mdp_PalDist'},'LPROC','lp_snapex')
%
% display DATA with labels derived from Praat TextGrid FOO (phones tier)
%   mview(data,'LABELS',{'foo','phones'})
%
% entering MVIEW alone will pop any active viewers forward, else display help
%

% mark tiede fecit
vers = 'mkt 19DEC23';

%-----------------------------------------------------------------------------
%	no args:  if any MVIEW viewers active, pop 'em forward, else show help

if nargin < 1,
	set(0,'ShowHiddenHandles', 'on');
	h = findobj('Tag', 'MVIEW');
	set(0,'ShowHiddenHandles', 'off');
	if isempty(h),
		eval('help mview');
	else,
		for i = 1 : length(h),
			figure(h(i));
		end;
	end;
	return;
end;


%-----------------------------------------------------------------------------
%	parse args

if ischar(varargin{1}),					% command line argument
	action = upper(varargin{1});
elseif isstruct(varargin{1}),			% mavis-compatible data
	action = 'INIT';
	data = varargin{1};
	varargin{1} = [];
elseif iscellstr(varargin{1}),			% variable list
	vList = varargin{1};
	if nargin > 1,
		args = varargin(2:end);
	else,
		args = [];
	end;
	args{end+1} = 'VLIST';
	args{end+1} = vList;
	mview(vList{1}, args{:});
	return;
else,		% load data from [nSamps x nDims x nChan] array (assume 250 Hz srate)
	if ndims(varargin{1})>=3 && isnumeric(varargin{1}),
		action = 'INIT';
		q = varargin{1};
		varargin{1} = [];
		data = struct('NAME',sprintf('%s1',inputname(1)),'SRATE',250,'SIGNAL',q(:,:,1));
		for k = 2 : size(q,3),
			data(end+1) = struct('NAME',sprintf('%s%d',inputname(1),k),'SRATE',250,'SIGNAL',q(:,:,k));
		end;
	else,
		error('MVIEW:  unrecognized data format');
	end;
end;


%-----------------------------------------------------------------------------
%	branch by action

switch action,

%-----------------------------------------------------------------------------
% ABORT:  force exit

	case 'ABORT',
		set(0,'ShowHiddenHandles', 'on');
		delete(findobj('Tag', 'MVIEW'));
		set(0,'ShowHiddenHandles', 'off');


%-----------------------------------------------------------------------------
% ABOUT:  display help

	case 'ABOUT',
		s = {'MVIEW  - work in progress';
			''
			['  ' vers]};
		helpwin(s, 'About MVIEW');
		
		
%-----------------------------------------------------------------------------
% AUTO:  toggle auto update status

	case 'AUTO',
		state = get(gcbf, 'userdata');
		s = get(gcbo,'checked');
		state.AUTO = strcmp(s,'off');
		set(gcbf, 'userdata', state);
		if state.AUTO, s = 'on'; else, s = 'off'; end;
		set(state.AUTOMENU, 'checked', s);
		if state.AUTO, SetBounds(state); end;
		

%-----------------------------------------------------------------------------
% CALLFCN:  call local function

	case 'CALLFCN',
		switch varargin{2},
			case 'ComputeF0',		% compute F0:  mview('CALLFCN','ComputeF0',state)
				mOut = ComputeF0wrapper(varargin{3});
			case 'ComputeSpectra',	% compute spectrum:  mview('CALLFCN','ComputeSpectra',state)
				[p,f,formants,bandwidths,amplitudes] = ComputeSpectra(varargin{3});
				mOut = {p,f,formants,bandwidths,amplitudes};
			case 'FitCircle',		% fit circle thru 3 circumference pts:  mview('CALLFCN','FitCircle',p)
				[c,r] = FitCircle(varargin{3});
				mOut = {c,r};
			case 'GetVals',			% get values at offset:  mview('CALLFCN','GetVals',state)
				[vals,labs] = GetVals(varargin{3});
				mOut = {vals,labs};
			case 'ParseTempMap',	% parse tempmap entry:  mview('CALLFCN','ParseTempMap',tNames,selName,[]);
				[ti,mod,comp] = ParseTempMap(varargin{3:5});
				if isempty(ti),
					mOut = ti;
				else,
					mOut = {ti,mod,comp};
				end;
			otherwise,
				error(sprintf('%s is not supported', varargin{1}));
		end;

		
%-----------------------------------------------------------------------------
% CFGSPAT:  configure spatial display
%
%	{2}:  callback ID

	case 'CFGSPAT',
		state = get(gcbf, 'userdata');
		curState = get(gcbo, 'checked');
		if strcmp(curState, 'on'), newState = 'off'; else, newState = 'on'; end;
		set(gcbo, 'checked', newState);
		switch varargin{2},
			case 1,		% toggle spline visibility
				set(state.SPLINEL, 'visible', curState);
			case 2,		% toggle fitted circle
				set(state.CIRCLEL, 'visible', newState);
				if strcmp(newState,'on'), SetCursor(state); end;
		end;
		
		
%-----------------------------------------------------------------------------
% CFGSPEC:  configure spectra analysis

	case 'CFGSPEC',
		state = get(gcbf, 'userdata');
		cfg = struct('NUDGE', state.NUDGE, ...
						'WSIZE', state.WSIZE, ...
						'ORDER', state.ORDER, ...
						'FRAME', state.FRAME, ...
						'AVGW', state.AVGW, ...
						'OLAP', state.OLAP, ...
						'PREEMP', state.PREEMP, ...
						'SOFF', state.SOFF, ...
						'SPECLIM', state.SPECLIM, ...
						'ANAL', state.ANAL, ...
						'MULT', state.MULT, ...
						'ISF', state.ISF);
		cfg = ConfigSpectra(cfg);
		if isempty(cfg), return; end;
		state.FRAME = cfg.FRAME;
		state.ORDER = cfg.ORDER;
		state.WSIZE = cfg.WSIZE;
		state.NUDGE = cfg.NUDGE;
		state.AVGW  = cfg.AVGW;
		state.OLAP  = cfg.OLAP;
		state.PREEMP= cfg.PREEMP;
		state.SOFF  = cfg.SOFF;
		if state.SOFF<=0, state.SOFF = 1; end;
		if state.SPECLIM ~= cfg.SPECLIM,
			specLim = cfg.SPECLIM;
			if specLim > state.SRATE/2, specLim = state.SRATE/2; end;
			state.SPECLIM  = specLim;
			set(state.SPECTRA, 'xlim', [1 specLim]);
		end;
		state.ANAL  = cfg.ANAL;
		state.MULT = cfg.MULT;
		state.ISF   = cfg.ISF;
		set(gcbf, 'userdata', state);
		SetCursor(state);
		SetBounds(state, 0);
		
		
%-----------------------------------------------------------------------------
% CFGTEMP:  configure temporal layout
%
%	{2}:  callback ID
%	{3}:  direction (UPDN)

	case 'CFGTEMP',

% initialize the dialog
		if strcmp(varargin{2}, 'INIT'),
			state = get(gcbf, 'userdata');
			loadedString = {state.DATA.NAME};
			displayedString = state.TEMPMAP;
			tempMap = TempCfg(loadedString,displayedString,{state.DATA.NCOMPS},{state.DATA.COLOR},gcbf);
			if isempty(tempMap), return; end;
			state = get(gcbf, 'userdata');
			state.TEMPMAP = tempMap;
			panDims = get(state.CURSORH, 'position');
%			delete(state.TPANELS.AXIS);
			for k = 1 : length(state.TPANELS), delete(state.TPANELS(k).AXIS); end
			[state.TPANELS,state.SPECGRAM] = InitTraj(state.DATA, state.DUR, panDims, state.SPREADS, state.TEMPMAP);
			set(gcbf, 'userdata', state);
			SetBounds(state, 3);
			return;
		end;

% dialog callback handlers
		hh = get(gcbf, 'userData');
		[h(1),h(2),h(3),h(4),h(5),h(6),h(7),h(8),h(9),h(10),h(11),defColor,fh] = deal(hh{:});
		loaded = h(1);
		displayed = h(2);
		content = h(3);
		movers = h(4:7);		% xfer, del, up, dn
		xyz = h(8:10);			% X, Y, Z
		kb = h(11);				% color info
% 		defColor = h(12:14);	% default color selection button bg
% 		fh = h(end);			% main figure handle
% 		h(12:end) = [];
		switch varargin{2},
			case 'LOADED',
				set(content, 'string', ' ', 'value', 1);
				set(h(3:end), 'enable', 'off');
				set(displayed, 'value', []);
				if ~isempty(get(gcbo, 'value')), set(movers(1), 'enable', 'on'); end;
			case 'DISPLAYED',
				set(loaded, 'value', []);
				switch length(get(gcbo, 'value')),
					case 0,		% no selection
						set(content, 'string', ' ', 'value', 1);
						set(h(3:end), 'enable', 'off');
						set(kb, 'backgroundColor', defColor);
					case 1,		% single selection
						set(movers(1), 'enable', 'off');
						set(movers(2:end), 'enable', 'on');
						loadedString = get(loaded, 'string');
						displayedString = get(displayed, 'string');
						displayedString = displayedString{get(displayed, 'value')};
						TempEnable(content, xyz, loadedString, displayedString, get(loaded,'userData'),kb);
					otherwise,	% multiple selection
						set(h([4 6:end]), 'enable', 'off');
						set(movers(2), 'enable', 'on');
						set(content, 'string', ' ', 'value', 1, 'enable', 'off');
						set(kb, 'backgroundColor', defColor);
				end;
			case 'XFER',
				displayedString = get(displayed, 'string');
				li = get(loaded, 'value');
				loadedString = get(loaded, 'string');
				if isempty(displayedString),
					displayedString = loadedString(li);
				else,
					displayedString = [displayedString ; loadedString(li)];
				end;
				set(displayed, 'string', displayedString);
			case 'DELETE',
				displayedString = get(displayed, 'string');
				displayedString(get(displayed, 'value')) = [];
				set(displayed, 'string', displayedString, 'value', []);
				set(content, 'string', ' ', 'value', 1);
				set(h(3:end), 'enable', 'off');
			case 'UPDN',
				displayedString = get(displayed, 'string');
				idx = [1:length(displayedString)];
				di = get(displayed, 'value');
				if varargin{3} < 0 & di > 1,
					idx = [idx(1:di-2) , di , idx(di-1) , idx(di+1:end)];
					di = di - 1;
				elseif varargin{3} > 0 & di < length(idx),
					idx = [idx(1:di-1) , idx(di+1) , di , idx(di+2:end)];
					di = di + 1;
				end;
				displayedString = displayedString(idx);
				set(displayed, 'string', displayedString, 'value', di);
			case 'XYZ',
				displayedString = get(displayed, 'string');
				di = get(displayed, 'value');
				sel = displayedString{di};
				k = find(sel(2:end)>'Z');
				if ~isempty(k), sel = sel(1:k(1)); end;
				comp = [get(xyz(1), 'value'),get(xyz(2), 'value'),get(xyz(3), 'value')];
				if sum(comp)>0 & sum(comp)~=get(content,'userData'),	
					s = 'xyz';
					sel = [sel , s(find(comp))];
				else,				% content userdata holds # comps this traj
					set(xyz(1:get(content,'userData')), 'value', 1);
				end;
				displayedString{di} = sel;
				set(displayed, 'string', displayedString);
			case 'CONTENT',
				displayedString = get(displayed, 'string');
				di = get(displayed, 'value');
				sel = displayedString{di};
				if sel(1) > 'Z', sel = sel(2:end); end;
				mod = get(content, 'value');
				if get(content, 'userData') > 1,	% movement
					if mod > 1,
						m = ' va';
						sel = [m(mod) , sel];
					end;
				else,								% mono-dimensional
					if mod > 1,
						k = find(sel>'Z');
						if ~isempty(k), sel = sel(1:k(1)-1); end;
						m = {'SPECT','F0','RMS','ZC','VEL','ABSVEL'};
						sel = [sel , '_' , m{mod-1}];
					end;
				end;
				displayedString{di} = sel;
				set(displayed, 'string', displayedString);
			case 'SETCOLOR',
				ti = get(kb, 'userData');				% selected trajectory
				state = get(fh, 'userData');
				rgb = uisetcolor(state.DATA(ti).COLOR, sprintf('Set color for %s', state.DATA(ti).NAME));
				state.DATA(ti).COLOR = rgb;
				set(fh, 'userData', state);
				set(kb, 'backgroundColor', rgb);
		end;
		
	
%-----------------------------------------------------------------------------
% CLONE:  duplicate window for copy, print visibility

	case 'CLONE',
		fh = gcbf;
		if isempty(fh),
			set(0,'ShowHiddenHandles', 'on');
			fh = findobj('Tag', 'MVIEW');
			set(0,'ShowHiddenHandles', 'off');
			fh = fh(1);
		end;
		state = get(fh, 'userdata');
		ch = colordef('new','black');
		set(ch, 'colormap', get(fh, 'colormap'), 'name', state.NAME, 'visible','on');
		switch varargin{2},
			case 1,					% temporal display
%				copyobj(flipud(cell2mat({state.TPANELS.AXIS})), ch);
                for k=1:length(state.TPANELS),ah(k)=double(state.TPANELS(k).AXIS);end
                copyobj(ah,ch);
				copyobj(state.FPANEL, ch);
				q = copyobj(state.CURSORH, ch);
				h = findobj(ch,'type','axes');
				for k = 1 : length(h), 
					p = get(h(k),'position');
					p = [.05 p(2) .9 p(4)];
					lh = findobj(h(k),'type','line');
					set(h(k),'hittest','on','position',p,'userData',lh);		% line handles saved as gca userdata
				end;
%				whitebg(ch);
				set(q,'color','none');
			case 2,					% spatial display
				copyobj(state.SPATIALA, ch);
				set(findobj(ch,'type','axes'),'buttonDownFcn','','position',[.1 .1 .8 .8]);
%				whitebg(ch);
			case 3,					% clone all
				copyobj(flipud(findobj(fh,'type','axes')), ch);
				set(findobj(ch,'type','patch'), 'edgeColor', [1 1 1], 'faceColor', 'none');
		
				uicontrol(ch, ...								% cursor
					'style', 'text', ...
					'horizontalAlignment', 'left', ...
					'string', sprintf('%-7s  %.1f', 'Cursor:', state.CURSOR), ...
					'units', 'characters', ...
					'backgroundColor', get(ch, 'color'), ...
					'foregroundColor', [1 1 1], ...
					'position', [4 3.5 15 1]);
				uicontrol(ch, ...								% head
					'style', 'text', ...
					'horizontalAlignment', 'left', ...
					'string', sprintf('%-7s  %.1f', 'Head:', state.HEAD), ...
					'units', 'characters', ...
					'backgroundColor', get(ch, 'color'), ...
					'foregroundColor', [1 1 1], ...
					'position', [4 2.0 15 1]);
				uicontrol(ch, ...								% tail
					'style', 'text', ...
					'horizontalAlignment', 'left', ...
					'string', sprintf('%-7s  %.1f', 'Tail:', state.TAIL), ...
					'units', 'characters', ...
					'backgroundColor', get(ch, 'color'), ...
					'foregroundColor', [1 1 1], ...
					'position', [4 0.5 15 1]);
		end;

%-----------------------------------------------------------------------------
% CLOSE:  close window

	case 'CLOSE',
		state = get(gcbf, 'userdata');
		if ~isempty(state.PPROC),
			pproc = state.PPROC;
			if ischar(pproc), 
				pproc = {pproc}; 
			elseif ischar(pproc{1}),
				pproc = {pproc};
			end;
			for k = 1 : length(pproc),
				pName = pproc{k};
				if iscell(pName), pName = pName{1}; end;
				feval(pName,state.PPSTATE{k},'CLOSE');
			end;
		end;
		delete(gcbf);
		global PLAYER
		clear PLAYER
		
		if exist('jheapcl'), jheapcl; end
		
%-----------------------------------------------------------------------------
% CONTRAST:  adjust spectrogram contrast

	case 'CONTRAST',
		state = get(gcbf, 'userdata');
		if isempty(state.SPECGRAM), return; end;
		colormap(flipud(gray(state.NGRAYS).^get(gcbo,'value')));
		for si = 1 : length(state.SPECGRAM),
			ka = state.TPANELS(state.SPECGRAM(si));
			ih = findobj(ka.AXIS, 'type', 'image');
			if isempty(ih), return; end;
	 		set(ih,'cdata', get(ih, 'cdata'));
		end;
		
%-----------------------------------------------------------------------------
% CURCHG:  manual cursor entry

	case 'CURCHG',
		state = get(gcbf, 'userdata');
		c = str2num(get(state.CURSORF, 'string'));
		if isempty(c),
			c = get(state.CURSORF, 'string');
			c = str2num(c(find(c>='0')));
			if isempty(c), c = state.CURSOR; end;
		end;
		if c < 0, c = 0; elseif c > state.DUR, c = state.DUR; end;
		state.CURSOR = c;
		set(state.CURSORF, 'string', sprintf(' %.1f',c));
		set(gcbf, 'userdata', state);
		SetCursor(state);
	
			
%-----------------------------------------------------------------------------
% CYCLE:  auto cursor updating

	case 'CYCLE',
		state = get(gcbf, 'userdata');
		cycling = state.MOTION;
		state.MOTION = varargin{2};			% direction:  -1, 0, 1, 99
		if ~cycling,
			saveANAL = state.ANAL;			% don't update spectrum while cycling
			state.ANAL = 0;
		end;
		set(gcbf, 'userdata', state);
		if ~cycling, 		% if not cycling, initiate it
			MotionLoop(state); 
		end;
		if ~cycling,
			state = get(gcbf, 'userdata');
			state.ANAL = saveANAL;			% restore spectral cross-section state
			set(gcbf, 'userdata', state);
			SetCursor(state);
		end;

		
%-----------------------------------------------------------------------------
% DOWN:  mouse down

	case 'DOWN',
		state = get(gcbf, 'userdata');
		xyz = get(gca, 'currentPoint');
		mod = get(gcbf, 'selectionType');
		x = xyz(1,1); y = xyz(1,2); z = xyz(1,3);
		
		switch varargin{2},
		
% click in framing panel is bounds adjust
			case 'FRAME',
				if strcmp(mod, 'open'),
					state.HEAD = 0;					% double click sets full selection
					state.TAIL = state.DUR;
					set(gcbf, 'userData', state);
					SetBounds(state);
					return;
				end;
				slop = state.DUR * .008;		% grabbing tolerance
				if state.HEAD>x-slop & state.HEAD<x+slop,
					state.MOVEMODE = 'HEAD';		% move head
				elseif state.TAIL>x-slop & state.TAIL<x+slop,
					state.MOVEMODE = 'TAIL';		% move tail
				elseif x>state.HEAD & x<state.TAIL,						
					state.MOVEMODE = -x;			% move selection (save starting point)
				else,
					return;
				end;
				state.MOVED = 0;
				set(gcbf, 'userData', state, ...
						'windowButtonMotionFcn', 'mview MOVESEL', ...
						'windowButtonUpFcn', 'mview UP');

% click in temporal panel sets cursor/label
			case 'TEMP',
				if strcmp(mod, 'open'), return; end;
				state.CURSOR = x;

% find clicked panel
				for tpi = 1 : length(state.TPANELS),
					xy = get(state.TPANELS(tpi).AXIS, 'currentPoint');
					y = xy(1,2);
					range = get(state.TPANELS(tpi).AXIS,'ylim');
					if (y>range(1) & y<range(2)),
						names = {state.DATA.NAME};
						nComps = {state.DATA.NCOMPS};
						set(state.CURSORFL, 'string', [' ',state.TEMPMAP{tpi}]);
						[ti,mo,comp] = ParseTempMap(names, state.TEMPMAP{tpi}, nComps); 
						state.CLICKINFO = [ti,tpi,mo,comp];
						if isempty(comp) & mo == 2,	% spectrogram
							set(state.XFL, 'string', 'Hz');
						end;
						break;
					end;
				end;
				
% update cursor
				SetCursor(state);

% handle modified click
				switch mod,
					case 'normal',	% (left button/unmodified click) fall thru
						state.MOVEMODE = 'CURSOR';		% cursor update
					case 'open', 	% (double-click)
						return;
					otherwise,		% (right button/modified click)
						if strcmp(mod, 'extend'),
							state.MOVEMODE = 'LBL_SILENT';	% shift:  silent labelling
						else,
							state.MOVEMODE = 'LBL_NOISY';	% ctl/alt: annotated labelling
						end;
						if ~isempty(state.LPROC),	% user proc labelling
							set(gcbf, 'userdata', state);	% update mode
							lpState = feval(state.LPROC, state.LPSTATE, 'DOWN', state.CURSOR);
							if ~isempty(lpState),
								state = get(gcbf, 'userData');
								state.LPSTATE = lpState;
								set(gcbf, 'userdata', state);	% allow state update
							end;
							return;
						end;
				end;
				set(gcbf, 'userdata', state, ...
					'windowButtonMotionFcn', 'mview MOVECUR', ...
					'windowButtonUpFcn', 'mview UP', ...
					'pointer', 'crosshair');

% click in spatial panel reports location
			case 'SPAT',
				if strcmp(mod, 'open'),
					mview('SPATPLOT', 'CLEAR');
					return;
				end;
				set(state.XF, 'string', sprintf(' %.1f',x));
				set(state.YF, 'string', sprintf(' %.1f',y));
				state.MOVEMODE = 'SPATIAL';
				set(gcbf, 'userData', state, ...
						'windowButtonMotionFcn', 'mview MOVESPAT', ...
						'windowButtonUpFcn', 'mview UP');

% click in spectrum panel reports location
			case 'SPECTRA',
				if ~strcmp(mod, 'normal'),		% modified click - plot spectrum in external window
					PlotSpectra(state);
					return;
				end;
				set(state.XFL, 'string', 'Hz');
				set(state.YFL, 'string', 'dB');
				set(state.XF, 'string', round(x));
				set(state.YF, 'string', sprintf(' %.1f',y));
				state.MOVEMODE = 'SPECTRA';
				set(gcbf, 'userData', state, ...
						'windowButtonMotionFcn', 'mview MOVESPEC', ...
						'windowButtonUpFcn', 'mview UP');
		end;

	
%-----------------------------------------------------------------------------
% GETCFG:  return current configuration
%
%	args:  state
	case 'GETCFG',
		state = varargin{2};
		mOut = struct('FIGPOS', get(gcbf, 'position'), ...	% figure position
					'FRAME', state.FRAME, ...		% # FFT evaluation points
					'ORDER', state.ORDER, ...		% LPC order
					'WSIZE', state.WSIZE, ...		% LPC evaulation window (msecs)
					'NFMTS', state.NFMTS, ...		% # recorded formants
					'NUDGE', state.NUDGE, ...		% nudge length (msecs)	
					'AVGW', state.AVGW, ...			% averaging window (msecs)
					'OLAP', state.OLAP, ...			% averaging overlap (msecs)
					'ZOOMW', state.ZOOMW, ...		% zoomed waveform window (msecs)
					'PREEMP', state.PREEMP, ...		% pre-emphasis (negated is adaptive)
					'SOFF', state.SOFF, ...			% SPL spectral offset
					'CONTRAST', get(state.CONTRAST, 'value'), ...	% spectrogram contrast value
					'AUTO', state.AUTO, ...			% auto update
					'FMTS', state.FMTS, ...			% formants overlay
					'DPROC', [], ...				% data proc
					'LPROC', state.LPROC, ...		% label proc
					'PPROC', [], ...				% ploting proc
					'LPSTATE', state.LPSTATE, ...	% label proc data
					'PALATE', state.PALATE, ...		% palate trace
					'PHARYNX', state.PHARYNX, ...	% pharyngeal line
					'ANAL', state.ANAL, ...			% spectra analysis
					'MULT', state.MULT, ...			% specgram multiplier
					'TEMPMAP', [], ...				% temporal display signal ordering
					'ISF', state.ISF, ...			% true if female subject
					'SPREAD', state.SPREAD, ...		% audio signal scaling (negative flags auto)
					'SPECLIM', state.SPECLIM, ...	% spectral display limit
					'SPLINE', state.SPLINE, ...		% spline point indices
					'CIRCLE', get(state.CIRCLEL,'visible'), ...	% TB circle
					'VIEW', state.VIEW, ...			% 3D view
					'SPATEX', [], ...				% spatial exclude list
					'IS3D', state.IS3D, ...			% 3D data
					'FTRAJ', state.FTRAJ, ...		% framing trajectory index
					'COLORS', []);					% trajectory colors
		mOut.TEMPMAP = state.TEMPMAP;	% must be done separately to avoid cloning
		mOut.PPROC = state.PPROC;
		mOut.DPROC = state.DPROC;
		mOut.SPATEX = state.SPATEX;
		mOut.COLORS = struct('NAME',state.DATA(1).NAME,'COLOR',state.DATA(1).COLOR);
		for ti = 2 : length(state.DATA),
			mOut.COLORS(ti) = 	struct('NAME',state.DATA(ti).NAME,'COLOR',state.DATA(ti).COLOR);	
		end
		
%-----------------------------------------------------------------------------
% INITialize  

	case 'INIT',

% parse PARAMS if any
		cfg = struct('FIGPOS', [], ...		% default figure position
					'FRAME', 256, ...		% # FFT evaluation points
					'ORDER', [], ...		% LPC order
					'WSIZE', 30, ...		% analysis window (msecs)
					'NFMTS', 3, ...			% # recorded formants
					'NUDGE', 5, ...			% nudge length (msecs)
					'AVGW', 6, ...			% averaging window (msecs)
					'OLAP', 1, ...			% averaging overlap (msecs)
					'ZOOMW', 10, ...		% zoomed waveform window (msecs)
					'PREEMP', .98, ...		% pre-emphasis (negated is adaptive)
					'SOFF', 20, ...			% SPL spectral offset (dB)
					'CONTRAST', 4, ...		% spectrogram contrast factor
					'AUTO', [], ...			% auto update
					'FMTS', [], ...			% formants overlay
					'DPROC', [], ...		% default data proc
					'LPROC', [], ...		% default label proc
					'PPROC', [], ...		% default plotting proc
					'LPSTATE', [], ...		% label proc data
					'PALATE', [], ...		% palate trace
					'PHARYNX', [], ...		% pharyngeal line
					'ANAL', 1, ...			% spectra analysis (LPC)
					'MULT', 1, ...			% specgram multiplier
					'TEMPMAP', [], ...		% temporal display signal ordering
					'ISF', 0, ...			% true if female subject
					'SPREAD', -1, ...		% audio signal scaling (auto)
					'SPECLIM', [], ...		% spectral display limit
					'SPLINE', 0, ...		% spline point indices
					'CIRCLE', 'off', ...	% TB circle
					'VIEW', [0 0], ...		% 3D view (old [27,20]
					'SPATEX', [], ...		% spatial exclude list
					'IS3D', [], ...			% 3D data (use algorithm to decide)
					'FTRAJ', 1, ...			% framing trajectory index
					'COLORS', []);			% trajectory colors
		vList = [];
		vListSel = [];
		head = 0;
		tail = [];
		labels = [];
		gotLabels = 0;
		if isfield(data,'LABELS'),			% explicitly specified labels override any labels already present in the data
			labels = data(1).LABELS;
			data = rmfield(data,'LABELS');
		end;
		name = inputname(1);
		if data(1).SRATE < 5000, cfg.ANAL = 0; end;
		if nargin > 2,
			i = 2;
			if isnumeric(varargin{2}), i = i + 1; end;
			while i < nargin,
				if ~ischar(varargin{i}),
					error(sprintf('argument error (arg %d)', i));
				end;
				switch upper(varargin{i}),
					case 'CONFIG',
						cfg = varargin{i+1};
						if ~isfield(cfg,'CIRCLE'), cfg.CIRCLE='off'; end;
						if ~isfield(cfg,'SPATEX'), cfg.SPATEX = []; end;
						if ~isfield(cfg,'IS3D'), cfg.IS3D = []; end;
					case 'LABELS',
						labels = varargin{i+1};
						gotLabels = 1;
					case 'LPROC',
						cfg.LPROC = varargin{i+1};
					case 'PALATE',
						cfg.PALATE = varargin{i+1};
					case 'PHARYNX',
						cfg.PHARYNX = varargin{i+1};
					case 'VLIST',	% variable list
						vList = varargin{i+1};
					case 'VLSEL',	% selection within it
						vListSel = varargin{i+1};
					case 'HEAD',
						head = varargin{i+1};
					case 'TAIL',
						tail = varargin{i+1};
					case 'NAME',
						name = varargin{i+1};
					case 'MAP',
						cfg.TEMPMAP = varargin{i+1};
					case 'SEX',
						cfg.ISF = (upper(varargin{i+1}(1)) == 'F');
					case 'SPREAD',
						cfg.SPREAD = varargin{i+1};
						if ischar(cfg.SPREAD), cfg.SPREAD = -1; end;
					case 'SPLINE',
						cfg.SPLINE = varargin{i+1};
					case 'VIEW',
						cfg.VIEW = varargin{i+1};
					case 'SPECLIM',
						cfg.SPECLIM = varargin{i+1};
					case 'DPROC',
						cfg.DPROC = varargin{i+1};
					case 'PPROC',
						cfg.PPROC = varargin{i+1};
					case 'IS3D',
						cfg.IS3D = varargin{i+1} == 1;
					case 'SPATEX',
						spatex = upper(varargin{i+1});
						if ~iscellstr(spatex), spatex = {spatex}; end;
						cfg.SPATEX = spatex;
					case 'FTRAJ',
						cfg.FTRAJ = varargin{i+1};
					case 'TEMPMAP',
						cfg.TEMPMAP = varargin{i+1};
					otherwise,
						error(sprintf('argument error:  %s', varargin{i}));
				end;
				i = i + 2;
			end;
		end;

% process DPROCs if any
		if ~isempty(cfg.DPROC),
			dproc = cfg.DPROC;
			if ischar(dproc), 
				dproc = {dproc}; 
			end;
			for di = 1 : length(dproc),
				dName = dproc{di}; dArgs = {[]};
				if iscell(dName),
					dArgs = dName{2};
					if ischar(dArgs), dArgs = {dArgs}; end;
					dName = dName{1};
				end;

% all DPROCS are passed palate trace, pharynx line, and labels
				data = feval(dName, data, dArgs{:}, {cfg.PALATE, cfg.PHARYNX, labels});
				if isfield(data,'LABELS');
					labels = data(1).LABELS;
					data = rmfield(data,'LABELS');
				end;
			end;
		end;

% strip contours from data, if any
		contours = [];
		if isfield(data(1),'CONTOURS'),
			contours = data(1).CONTOURS;
			data = rmfield(data,'CONTOURS');
		end;
		
% update labels if necessary
		if gotLabels,		
			if isnumeric(labels),		% convert offset vector into labels array
				vals = labels(:);
				labels = struct('NAME','','OFFSET',vals(1),'VALUE',[],'HOOK',[]);
				for k = 2 : length(vals),
					labels(k) = struct('NAME','','OFFSET',vals(k),'VALUE',[],'HOOK',[]);
				end;
			elseif ~isstruct(labels),	% load from Praat TextGrid
				try,
					if ischar(labels),
						fn = labels; tier = 1;
					else,
						fn = labels{1}; tier = labels{2};
					end;
					[segs,labs] = ReadPraatTier(fn,tier);
					if size(segs,2) > 1,		% label only left edge of labelled interval tiers
						k = find(~cellfun(@isempty,labs)); vals = segs(k,1)*1000; labs = labs(k);
					end;
					labels = struct('NAME',labs{1},'OFFSET',vals(1),'VALUE',[],'HOOK',[]);
					for k = 2 : length(vals),
						labels(k) = struct('NAME',labs{k},'OFFSET',vals(k),'VALUE',[],'HOOK',[]);
					end;
				catch,
					error('unable to load labels from Praat TextGrid %s', fn);
				end;
			end;
		end;

% reload labels from <NAME>_lbl if defined in base workspace
		if isempty(labels),
			if isempty(vListSel), vListSel = 1; end;
			if ~isempty(vList) && isempty(name), name = vList{vListSel}; end;
			if evalin('base',sprintf('exist(''%s_lbl'',''var'')',name)),
				labels = evalin('base',[name '_lbl']);
			end;
		end;
		names = {data.NAME};
		if isfield(data, 'LABELS'),
			labs = {data.LABELS};
			data = rmfield(data, 'LABELS');
			try,
				q = cell2mat(labs');
				labs = labs(1);				% if all same size assume duplicate, remove
			catch,
				;
			end;
			for k = find(~cellfun('isempty',labs)),
				lab = labs{k};
				for n = 1 : length(lab),				
					if isfield(lab,'NOTE'),
						hook = names{k};		% bw combatibility:  load MAVIS source traj
					else,
						hook = lab(n).HOOK;
					end;
					newLab = struct('NAME', lab(n).NAME, ...
										'OFFSET', lab(n).OFFSET, ...
										'VALUE', [], ...
										'HOOK', []);
					newLab.VALUE = lab(n).VALUE;
					newLab.HOOK = hook;
					if isempty(labels), labels = newLab; else, labels(end+1) = newLab; end;
				end;
			end;
		end;

% set up window
		if isempty(cfg.FIGPOS),
			figPos = get(0, 'ScreenSize');
			dh = min([figPos(4) 1000]);
			dw = min([figPos(3) 1200]);
			set(0,'ShowHiddenHandles', 'on');
			nw = length(findobj('Tag', 'MVIEW'));
			set(0,'ShowHiddenHandles', 'off');
			switch computer,
				case 'MAC2', figPos = [8+nw*6  , figPos(4)-dh+51-nw*20 , dw-42 , dh-92];
				case 'PCWIN',figPos = [6+nw*10 , figPos(4)-dh+33-nw*24 , dw-22 , dh-74];
				otherwise,   figPos = [6+nw*10 , figPos(4)-dh+36-nw*24 , dw-22 , dh-85];
			end;
		else,
			figPos = cfg.FIGPOS;
		end;

		fh = colordef('new', 'black');		% figure handle
		set(fh, ...
			'tag', 'MVIEW', ...
			'numberTitle', 'off', ...
			'position', figPos, ...
			'menubar', 'none', ...
			'pointer', 'crosshair', ...
			'visible', 'off', ...
			'CloseRequestFcn', 'mview CLOSE');
		if get(0,'ScreenDepth') < 16, 	
			nGrays = 32; 	
		else,	
			nGrays = 256; 	
		end;

% parse input dataset
		[data,spatChan,dur,minDur,spreads,range,is3D,audioSpread] = ParseData(data, cfg.SPREAD, cfg.SPATEX);
		if ~isempty(cfg.IS3D), is3D = cfg.IS3D; end;
		spreads = spreads * 1.1;		% pad
		if ~isempty(cfg.PALATE),
			if size(cfg.PALATE,2) < 3,
				range(1,1:2) = min([range(1,1:2) ; min(cfg.PALATE)]);
				range(2,1:2) = max([range(2,1:2) ; max(cfg.PALATE)]);
			else,
				range(1,:) = min([range(1,:) ; min(cfg.PALATE)]);
				range(2,:) = max([range(2,:) ; max(cfg.PALATE)]);
			end;
		end;
		if ~isempty(contours),
			range(1,1) = min([range(1,1),min(contours(:,1,:),[],'all')]);
			range(1,2) = min([range(1,2),min(contours(:,2,:),[],'all')]);
			range(1,3) = min([range(1,3),min(contours(:,3,:),[],'all')]);
			range(2,1) = max([range(2,1),max(contours(:,1,:),[],'all')]);
			range(2,2) = max([range(2,2),max(contours(:,2,:),[],'all')]);
			range(2,3) = max([range(2,3),max(contours(:,3,:),[],'all')]);
		end;
		if ~isempty(cfg.PHARYNX),
			range(1,1:2) = min([range(1,1:2) ; min(cfg.PHARYNX)]);
			range(2,1:2) = max([range(2,1:2) ; max(cfg.PHARYNX)]);
		end;
		if ~isempty(spatChan),
			v = min([max(diff(range)),5]);
			range = range + repmat([-v;v],1,size(range,2));	% overall trajectory range [min,max x x,y,z]
		end;
		if ~is3D, range(:,3) = [0;1]; end;
		cfg.SPREAD = audioSpread;

% get default spline points
		if isempty(cfg.SPLINE),
			tn = char({data.NAME}');
			ti = tn(:,1) == 'T';
			if length(ti) > 3, cfg.SPLINE = find(ti); end;
		end;

% assign colors
		if isfield(data,'COLOR'),
			spatColors = cell2mat({data(spatChan).COLOR}');
		else,
			if ~isempty(spatChan),
				spatColors = hsv(length(spatChan)+1);			% spatial plotting colors
				spatColors = [spatColors([2:2:end],:) ; spatColors([1:2:end],:)];
			end;
			if isfield(cfg,'COLORS') && ~isempty(cfg.COLORS),
				names = {data(spatChan).NAME};
				for n = 1 : length(names),
					k = find(strcmp(names{n},{cfg.COLORS.NAME}));
					if ~isempty(k), spatColors(n,:) = cfg.COLORS(k).COLOR; end;
				end;
			end;			
			for ti = 1 : length(data),
				data(ti).COLOR = [1 1 1];
				k = find(ti == spatChan);
				if ~isempty(k), data(ti).COLOR = spatColors(k,:); end;
			end;
		end;
		
% spatial display axis
		menu = uicontextmenu;
		uimenu(menu, 'label', 'Hue Plot', ...
				'callback', 'mview(''SPATPLOT'',''HUE'')');
		uimenu(menu, 'label', 'History Plot', ...
				'callback', 'mview(''SPATPLOT'',''HISTORY'')');
		uimenu(menu, 'label', 'Clear', ...
				'separator', 'on', ...
				'callback', 'mview(''SPATPLOT'',''CLEAR'')');
		sa = axes('position', [.05 .57 .347 .4], ...
			'box', 'on', ...
			'uicontextmenu', menu);
		circleH = [];
		if isempty(spatChan),							% if nothing to plot							
			set(sa, 'xtick',[], 'ytick',[]);
			sh = [];
			splineH = [];
		else,
			set(sa, 'xlim', range(:,1), ...
				'ylim', range(:,2), ...
				'zlim', range(:,3), ...
				'dataAspectRatio', [1 1 1], ...
				'buttonDownFcn', 'mview(''DOWN'',''SPAT'')');
			x = range(1,1) - 10;
			y = range(1,2) - 10;						% create points (initially out of axis)
			z = range(1,3);
			if is3D, z = z - 10; end;
			for ci = 1 : length(spatChan),
				sh(ci) = xorline(x, y, z, ...
					'marker', '.', ...
					'markerSize', 20, ...
					'hitTest', 'off', ...
					'color', spatColors(ci,:));
			end;
			if is3D,
				splineH = xorline(x, y, z, 'color', [.7 .7 .7], 'hitTest', 'off', 'linewidth', 1.5);
				if ~isempty(cfg.PALATE),
					line(cfg.PALATE(:,1), cfg.PALATE(:,2), cfg.PALATE(:,3), 'color', 'y', 'hitTest', 'off', 'linewidth',1.5);
				end;
			else,
				splineH = xorline(x, y, 'color', [.7 .7 .7], 'hitTest', 'off');
				circleH = xorline(x, y, 'color', [.7 .7 .7], 'hitTest', 'off', 'visible',cfg.CIRCLE);
				if ~isempty(cfg.PALATE),
					line(cfg.PALATE(:,1), cfg.PALATE(:,2), 'color', 'y', 'hitTest', 'off');
				end;
			end;
			if ~isempty(cfg.PHARYNX),
				line(cfg.PHARYNX(:,1), cfg.PHARYNX(:,2), 'color', 'y', 'hitTest', 'off');
			end;
		end;
		ylabel('mm');
		if is3D, view(cfg.VIEW); end;

% framing panel
		fi = cfg.FTRAJ;
		fa = axes('position', [.4 .87 .59 .1], ...		% framing axis
			'box', 'on','hitTest','off');
		if isempty(tail),
			tail = dur;
		elseif tail <= head,
			tail = head + minDur;
			if tail > dur, tail = dur; end;
		elseif tail > dur,
			tail = dur;
		end;
		if head > tail-minDur, head = tail-minDur; end;
		sRate = data(fi).SRATE;
		ts = floor(dur*sRate/1000)+1;
		s = data(fi).SIGNAL(1:ts,1);
		dsMax = max(abs(s));						% signal range
		ds = data(fi).SPREAD;						% plotting range
		if size(data(fi).SIGNAL,2) > 1,
			ds = [min(s) max(s)];
			ds = ds + [-.1 .1]*diff(ds);
		end;
		plot(s, 'w');
		set(fa, 'xtick', [], 'ytick', [], ...
			'xlim', [1 ts], 'ylim', ds);
		hold on;
		switch computer,				% selector patch handle colors
			case 'MAC2', ec = [.2 .2 .2];
			case 'PCWIN',ec = [.3 .3 .3];
			otherwise,   ec = [.25 .25 .25];
		end;
		ht = floor([head tail]*sRate/1000)+1;		
		bh = patch([ht(1) ht(1) ht(2) ht(2)], [ds(1) ds(2) ds(2) ds(1)], ec, 'EdgeColor', ec);
		if verLessThan('matlab','8.4.0'), set(bh, 'eraseMode','xor'); else, set(bh, 'faceAlpha',.6); end
		hold off;
		axes('position', [.4 .87 .59 .1],'color','none', ...
			'xlim', [0 dur], 'ylim', [0 1], ...
			'xtick', [], 'ytick', [], ...
			'buttonDownFcn', 'mview(''DOWN'',''FRAME'')');
		
% spectra axis
		if isempty(cfg.SPECLIM), 
			specLim = sRate/2;
			cfg.SPECLIM = specLim;
		else,
			specLim = cfg.SPECLIM;
			if specLim > sRate/2, specLim = sRate/2; end;
		end;
		ra = axes('position', [.05 .2 .347 .327], ...
			'xlim', [1 specLim], 'ylim', [5 100], ...
			'box', 'on', 'buttonDownFcn', 'mview(''DOWN'',''SPECTRA'')');
		rl1 = xorline(0, 0, 'color', 'w', 'buttonDownFcn', 'mview(''DOWN'',''SPECTRA'')');
		rl2 = xorline(0, 0, 'color', 'c', 'buttonDownFcn', 'mview(''DOWN'',''SPECTRA'')');
		grid on;
		xlabel('Hz');
		ylabel('dB');
		
% zoom axis
		menu = uicontextmenu;
		uimenu(menu, 'label', 'Plot', 'callback', 'mview(''ZOOM'',0)');
		uimenu(menu, 'label', '5 ms', 'separator', 'on', 'callback', 'mview(''ZOOM'',5)');
		uimenu(menu, 'label', '10 ms', 'callback', 'mview(''ZOOM'',10)');
		uimenu(menu, 'label', '20 ms', 'callback', 'mview(''ZOOM'',20)');
		uimenu(menu, 'label', '50 ms', 'callback', 'mview(''ZOOM'',50)');
		ns = floor(cfg.ZOOMW*sRate/1000);
		if ns < 10, ns = 10; cfg.ZOOMW = 1000*ns/sRate; end;
		za = axes('position', [.25 .04 .147 .12], ...
			'xtick', [], 'ytick', [], ...
			'xlim', [1 ns], 'ylim', [-dsMax dsMax], ...			
			'box', 'on', ...
			'uicontextmenu', menu);
		xlabel(sprintf('%g msecs', cfg.ZOOMW));
		lh = get(za,'xlabel');
		set(lh,'units','normal');
		pos = get(lh,'position');
		pos(1) = .75;
		set(lh,'position',pos);
		line(round(ns/2)*[1 1],ds,'color','g','linestyle',':','tag','CURSOR');
		zoom = xorline(0,0,'color','w', 'userData', za);
		zsh = uicontrol(fh, ...
			'style', 'slider', ...
			'min', 1, 'max', 50, ...
			'value', cfg.ZOOMW, ...
			'units', 'normal', ...
			'position', [.249 0.022 .07 .015], ...
			'toolTipString', 'Adjust zoomed window length', ...
			'callback', 'mview ZOOM');
		set(za, 'userData', zsh);

% default temporal panel layout:  audio, spectrogram (double panel), movement
		if isempty(cfg.TEMPMAP),
			cfg.TEMPMAP = {data.NAME};
			if data(1).SRATE > 1000,
				cfg.TEMPMAP = [cfg.TEMPMAP(1) , {[cfg.TEMPMAP{1} '_SPECT']} , cfg.TEMPMAP(2:end)]; 
			end;
		end;
		panDims = [.4 .04 .59 .825];			% panel dimensions (normalized)
		[th,ki] = InitTraj(data, dur, panDims, spreads, cfg.TEMPMAP);
		if ~isstruct(th),
			delete(fh);
			error('%s not found in %s', ki, name);
		end;
		
% cursor axis
		hold on;										% cursor axis
		ca = axes('position', panDims, ...
					'xlim', [0 dur], 'ylim', [0 1], ...
					'ytick', [], 'color', 'none', ...
					'interruptible','off', 'busyAction','cancel', ...
					'buttonDownFcn', 'mview(''DOWN'',''TEMP'')');
		cl = xorline([0 0], [0 1], 'color', 'white', ...	% cursor line handle
					'interruptible','off', 'busyAction','cancel', ...
					'buttonDownFcn', 'mview(''DOWN'',''TEMP'')');
		hold off;
		xlabel('msecs');
		
% set up text fields, menus
		auto = cfg.AUTO;
%		if isempty(auto) && length(data(fi).SIGNAL) > 50000, auto=0; else, auto=1; end;
		if isempty(auto), auto=1; end;
		if ~isfield(cfg,'FMTS'), cfg.FMTS = []; end;
		if ~isfield(cfg,'PPROC'), cfg.PPROC = []; end;
		fmts = cfg.FMTS;
		if isempty(fmts) || length(data(fi).SIGNAL) > 50000, fmts=0; end;
		[cfl,cf,hf,tf,xfl,xf,yfl,yf,zfl,zf,slider,autoMenu,lblMenu,fmtsMenu] = InitControls(fh,cfg.CONTRAST,cfg.LPROC,auto,is3D,fmts);

		if ~isempty(vList),			% variable list menu
			menu = uimenu(fh, 'label', 'Variables', 'HandleVisibility', 'Callback');
			cs = {'off','on'};
			if isempty(vListSel), vListSel = 1; end;
			if isempty(name), name = vList{vListSel}; end;
			uimenu(menu, 'label', 'Previous', ...
				'accelerator', '1', ...
				'callback', 'mview(''VARLIST'',-1);');
			uimenu(menu, 'label', 'Next', ...
				'accelerator', '2', ...
				'callback', 'mview(''VARLIST'',1);');
			uimenu(menu, 'label', 'Next; close current', ...
				'accelerator', '3', ...
				'callback', 'mview(''VARLIST'',1);close(gcbf);');
			uimenu(menu, 'label', 'Next plus export', ...
				'accelerator', '4', ...
				'callback', 'mview(''LEXPORT'');mview(''VARLIST'',1);');
			uimenu(menu, 'label', 'Next; export, close current', ...
				'accelerator', '5', ...
				'callback', 'mview(''LEXPORT'');mview(''VARLIST'',1);close(gcbf);');
			uimenu(menu, 'label', 'Next; save labs, close current', ...
				'accelerator', '6', ...
				'callback', 'mview(''LSAVE'',1);mview(''VARLIST'',1);close(gcbf);');
			uimenu(menu, 'label', 'Next; export/save labs, close current', ...
				'accelerator', '7', ...
				'callback', 'mview(''LEXPORT'');mview(''LSAVE'',1);mview(''VARLIST'',1);close(gcbf);');
			uimenu(menu, 'label', vList{1}, ...
				'separator', 'on', ...
				'checked', cs{(vListSel==1)+1}, ...
				'userData', 1, ...
				'callback', 'mview(''VARLIST'',0)');
			for i = 2 : length(vList),
				uimenu(menu, 'label', vList{i}, ...
					'checked', cs{(vListSel==i)+1}, ...
					'userData', i, ...
					'callback', 'mview(''VARLIST'',0)');			
			end;
		end;

% init internal state
		if isempty(cfg.ORDER),
			if cfg.ISF,
				cfg.ORDER = round(sRate/1000)+8;	% female
			else,
				cfg.ORDER = round(sRate/1000)+4;	% male
			end;
		end;
		state = struct('FH', fh, ...				% figure handle
						'FPANEL', fa, ...			% framing panel handle
						'FTRAJ', cfg.FTRAJ, ...		% framing trajectory index
						'BOUNDS', bh, ...			% selector bounds (patch) handle
						'SPATIALA', sa, ...			% spatial axis
						'SPATIALH', sh, ...			% spatial handles
						'TPANELS', th, ...			% temporal panel handles
						'TEMPMAP', [], ...			% temporal trajectory ordering
						'SPREADS', spreads, ...		% common vertical scaling for movement, vel, acc
						'SPECGRAM', ki, ...			% spectrogram panel index
						'MULT', cfg.MULT, ...		% spectrogram multiplier (1: wide ... 4: narrow)
						'CONTRAST', slider, ...		% spectrogram contrast
						'NGRAYS', nGrays, ...		% # available grays
						'SPECTRA', ra, ...			% spectra panel handle
						'SPECTRAL', [rl1 rl2], ...	% spectra line handles
						'ZOOM', zoom, ...			% zoomed waveform line handle
						'CURSORH', ca, ...			% cursor axis handle
						'CURSORL', cl, ...			% cursor line handle
						'CURSORF', cf, ...			% cursor field handle
						'CURSORFL', cfl, ...		% cursor label handle
						'CURSOR', 0, ...			% cursor (msecs)
						'HEADF', hf, ...			% head field handle
						'HEAD', head, ...			% head (msecs)
						'TAILF', tf, ...			% tail field handle
						'TAIL', tail, ...			% tail (msecs)
						'DUR', dur, ...				% duration of shortest signal
						'MINDUR', minDur, ...		% min possible duration
						'XF', xf, ...				% X value field handle
						'XFL', xfl, ...				% X label handle
						'YF', yf, ...				% Y value field handle
						'YFL', yfl, ...				% Y label handle
						'ZF', zf, ...				% Y value field handle
						'ZFL', zfl, ...				% Z label handle
						'IS3D', is3D, ...			% true for 3D data
						'NUDGE', cfg.NUDGE, ...		% nudge step (msecs)
						'FRAME', cfg.FRAME, ...		% # FFT evaluation points
						'ORDER', cfg.ORDER, ...		% LPC order
						'WSIZE', cfg.WSIZE, ...		% analysis window size (msecs)
						'NFMTS', cfg.NFMTS, ...		% # formants recorded
						'AVGW', cfg.AVGW, ...		% averaging window (msecs)
						'OLAP', cfg.OLAP, ...		% averaging overlap (msecs)
						'ZOOMW', cfg.ZOOMW, ...		% zoomed waveform window (msecs)
						'PREEMP', cfg.PREEMP, ...	% pre-emphasis (negated is adaptive)
						'SOFF', cfg.SOFF, ...		% spectral offset
						'ANAL', cfg.ANAL, ...		% spectra analysis
						'ISF', cfg.ISF, ...			% true if female subject
						'SPREAD', cfg.SPREAD, ...	% audio scaling
						'SPECLIM', specLim, ...		% spectral display limit (Hz)
						'SPLINE', cfg.SPLINE, ...	% spline point indices
						'SPLINEL', splineH, ...		% spline line
						'CIRCLEL', circleH, ...		% circle line
						'VIEW', cfg.VIEW, ...		% 3D view
						'SPATEX', [], ...			% spatial exclude list
						'DPROC', [], ... 			% preprocessing procedure
						'LPROC', cfg.LPROC, ...		% labelling procedure
						'LPSTATE', cfg.LPSTATE, ...	% labelling procedure data
						'PPROC', [], ...			% plotting procedure
						'PPSTATE', [], ...			% plotting proc data
						'PALATE', cfg.PALATE, ...	% palate trace
						'PHARYNX', cfg.PHARYNX, ...	% pharyngeal line
						'DATA', data, ...			% concurrently sampled dataset
						'FI', fi, ...				% framing data index
						'SRATE', sRate, ...			% framing data sampling rate
						'SPATCHAN', spatChan, ...	% spatial data indices
						'MOVEMODE', 0, ...			% movement mode
						'MOVED', 0, ...				% movement flag
						'MOTION', 0, ...			% cycling flag
						'CLICKINFO', [], ...		% clicked trajectory info [index,panel,mod,comp]
						'AUTOMENU', autoMenu, ...	% auto update menu handle
						'AUTO', auto, ...			% auto update enabled
						'FMTSMENU', fmtsMenu, ...	% formants overlay menu handle
						'FMTS', fmts, ...			% formants overlay enabled
						'LBLMENU', lblMenu, ...		% labelling behavior menu handle
						'LABELS', [], ...			% label list
						'NAME', name, ...			% input data name
						'INTERPMODE', 1, ...		% 0: floor, 1: round, 2: linear, 3: cubic interp
						'CONTOURS', contours, ...	% aligned contours
						'VLIST', [], ...			% variable list
						'VLISTSEL', vListSel);		% current varlist selection
		
% these assignments must be done separately to avoid cloning state
		state.TEMPMAP = cfg.TEMPMAP;
		state.DPROC = cfg.DPROC;
		state.PPROC = cfg.PPROC;
		state.SPATEX = cfg.SPATEX;
		if ~isempty(vList), state.VLIST = vList; end;

% update selection
		SetBounds(state, 2);
		SetCursor(state);
		
% plot any labels
		if ~isempty(labels),
			if ~isempty(cfg.LPROC),
				set(fh, 'userData', state);
			end;
			axes(state.CURSORH);
			y = get(state.CURSORH, 'yLim') * .99;
			labels(1).HANDS = [];
			for i = 1 : length(labels),
%				if isempty(cfg.LPROC) || isempty(cfg.LPSTATE),
				if isempty(cfg.LPROC),
					x = labels(i).OFFSET;
					labels(i).HANDS = xorline([x x], y, 'tag', 'LABEL', 'color','y', ...
											'buttonDownFcn', 'mview(''LMOVE'',''DOWN'');');
					if ~isempty(labels(i).NAME),
						labels(i).HANDS(end+1) = text(x, y(2), [' ', labels(i).NAME], ...
							'verticalAlignment', 'top', ...
							'tag', 'LABEL', ...
							'interpreter','none', ...
							'fontname', 'geneva', ...
							'fontsize', 9);
						if verLessThan('matlab','8.4.0'), set(labels(i).HANDS(end),'eraseMode','xor'); end
					end;
				else,
					labels(i) = feval(cfg.LPROC, cfg.LPSTATE, 'PLOT', labels(i), y, fh);
				end;
			end;
			state.LABELS = labels;
			set(fh, 'userData', state);
		end;

% save state, turn on display
		set(fh, 'userdata', state, 'name', ['MVIEW:  ' name], 'visible','on');			

% init plotting procedures
		if ~isempty(cfg.PPROC),
			pproc = cfg.PPROC;
			if ischar(pproc), 
				pproc = {pproc}; 
			elseif ischar(pproc{1}),
				pproc = {pproc};
			end;
			for k = 1 : length(pproc),
				pName = pproc{k}; pArgs = {};
				if iscell(pName),
					pArgs = pName{2};
					if ischar(pArgs), pArgs = {pArgs}; end;
					pName = pName{1};
				end;
				state.PPSTATE{k} = feval(pName, state, 'INIT', pArgs{:});
			end;
			set(fh, 'userData', state);
		end;

% config label proc if necessary
		if isunix,				% focus X
 			[s,r] = unix('osascript -e ''tell application "MATLAB" to activate''');
 		end;
		if ~isempty(cfg.LPROC) & isempty(cfg.LPSTATE),
			lpState = feval(cfg.LPROC, [], 'CONFIG', state);	% call user proc config handler
			if ~isempty(lpState),
				updateLabs = 0;
				if isnumeric(lpState) & lpState == -1,		% call label procedure immediately
					set(fh, 'handleVisibility', 'on');
					feval(state.LPROC, [], 'DOWN', 0, 1, fh);
					if ~state.AUTO, SetBounds(get(fh, 'userData'),0); end;
					set(fh, 'handleVisibility', 'callback');
				elseif iscell(lpState),
					state.LPSTATE = lpState{1};
					set(fh, 'userdata', state);
					updateLabs = lpState{2};
				else,
					state.LPSTATE = lpState;				% store configured label state
					set(fh, 'userdata', state);
				end;
				if updateLabs && ~isempty(state.LABELS),
					labels = state.LABELS;
					delete(cell2mat({labels.HANDS}));
					for li = 1 : length(labels),
						axes(state.CURSORH);
						y = get(state.CURSORH, 'yLim') * .99;
						labels(li) = feval(state.LPROC, state.LPSTATE, 'PLOT', labels(li), y, fh);
					end;
					set(cell2mat({labels.HANDS}),'visible','on');
					state.LABELS = labels;
					set(fh, 'userData', state);
				end;
			end;
		end;

% set callback handlevisibility
		set(fh, 'handleVisibility','callback');
		

%-----------------------------------------------------------------------------
% LCLEAR:  clear all labels

	case 'LCLEAR',
		if strcmp(questdlg('Clear all labels...', 'Verify...', 'Yes', 'No', 'Yes'), 'Yes'),
			state = get(gcbf, 'userdata');
			state.LABELS = [];
			set(gcbf, 'userdata', state);
			delete(findobj(state.CURSORH, 'tag', 'LABEL'));
			if isfield(state.LPSTATE,'DELBOX') & state.LPSTATE.DELBOX,
				delete(findobj(state.FH, 'tag', 'GESTBOX'));
			end;
		end;
		
%-----------------------------------------------------------------------------
% LCLRSEL:  clear selected labels

	case 'LCLRSEL',
		cfgState = get(gcbf, 'UserData');
		state = get(cfgState.GUI, 'UserData');
		killList = get(cfgState.LISTBOX, 'Value');
		if isempty(killList), return; end;
		curLabs = size(get(cfgState.LISTBOX, 'String'),1);
		for i = killList,
			delete(state.LABELS(i).HANDS);
		end;
		state.LABELS(killList) = [];
		set(cfgState.GUI, 'UserData', state);
		set(cfgState.LISTBOX, 'Value', [], 'String', MakeList(state));
		
%-----------------------------------------------------------------------------
% LCONFIG:  configure labelling

	case 'LCONFIG',
		state = get(gcbf, 'userdata');
		width = 280;
		height = 180;
		pos = CenteredDialog(gcbf, width, height);
		
		cfg = dialog('Name', 'Default Labelling Behavior', ...
			'Tag', 'MVIEW', ...
			'menubar', 'none', ...
			'Position', pos, ...
			'KeyPressFcn', 'set(gcbf,''UserData'',1);uiresume', ...
			'UserData', 0);
		
		blurb = ['A label is set at cursor offset on modified click release.  ' ...
				'Use shift-click to create label without annotation; ctl/alt-click ' ...
				'to create an annotated label.'];
		
		h = 0;
		uicontrol(cfg, ...
			'Style', 'frame', ...
			'Position', [10 height-90+h width-20 80-h]);
		uicontrol(cfg, ...
			'Style', 'text', ...
			'HorizontalAlignment', 'left', ...
			'String', blurb, ...
			'Position', [13 height-87+h width-26 74-h]);

		v = state.LPSTATE;
		if isstruct(v) | isempty(v) | v<1, v = 0; else, v = 1; end;
		propLab = uicontrol(cfg, ...	% propagate labels checkbox
			'Style', 'checkbox', ...
			'String', 'Propagate labels', ...
			'Value', v, ...
			'Units', 'characters', ...
			'Position', [8 7 30 1.5]);
		
		uicontrol(cfg, ...		% buttons
			'Position',[width/2-70 15 60 25], ...
			'String','OK', ...
			'Callback','set(gcbf,''UserData'',1);uiresume');
		uicontrol(cfg, ...
			'Position',[width/2+10 15 60 25], ...
			'String','Cancel', ...
			'Callback','uiresume');
		
% wait for input
		uiwait(cfg);
		if ~ishandle(cfg), return; end;
		if get(cfg, 'userData'),
			state.LPSTATE = get(propLab, 'value');
			set(gcbf, 'userData', state);
		end;
		delete(cfg);
		
			
%-----------------------------------------------------------------------------
% LEDIT:  edit labels

	case 'LEDIT',
		state = get(gcbf, 'userdata');
		width = 350;
		height = 250;
		pos = CenteredDialog(gcbf, width, height);

		cfg = dialog('Name', 'Edit Labels', ...
			'Position', pos, ...
			'HandleVisibility','off', ...
			'keyPressFcn', 'uiresume');

		h = 19;
        w = 0;
        pc = strcmp(computer, 'PCWIN');
        if pc, w = 9; h = 17; end;
		uicontrol(cfg, ...
			'HorizontalAlignment', 'center', ...
			'units', 'characters', ...
			'Position', [2 h 7 1], ...
			'String','Label', ...
			'Style','text');
		uicontrol(cfg, ...
			'HorizontalAlignment', 'center', ...
			'units', 'characters', ...
			'Position', [18+w h 8 1], ...
			'String','Offset', ...
			'Style','text');
		uicontrol(cfg, ...
			'HorizontalAlignment', 'center', ...
			'units', 'characters', ...
			'Position', [27+w h 10 1], ...
			'String','Comments', ...
			'Style','text');
			
		lb = uicontrol(cfg, ...		% listbox
			'Position',[10 60 width-20 height-90], ...	
			'FontName', 'Courier', ...
			'String', MakeList(state), ...	
			'Style','listbox', ...
			'Max', 2, ...
			'Value', [], ...
			'UserData', [], ...
			'Callback','mview LEDSEL;');
			
		uicontrol(cfg, ...		% buttons
			'Position',[width/2-65 15 60 25], ...
			'String', 'Edit', ...
			'callback', 'mview LEDSEL');
		uicontrol(cfg, ...
			'Position',[width/2+5 15 60 25], ...
			'String', 'Delete', ...
			'callback', 'mview LCLRSEL');
			
		cfgState = struct('GUI', gcbf, 'LISTBOX', lb);
		set(cfg, 'userdata', cfgState);
			
% wait for input
		uiwait(cfg);
		if ishandle(cfg), close(cfg); end;
		

%-----------------------------------------------------------------------------
% LEXPORT:  default label export (write offsets to spreadsheet file)

	case 'LEXPORT',
		state = get(gcbf, 'userdata');
		if ~isempty(state.LPROC) & nargin < 2,
			feval(state.LPROC, state.LPSTATE, 'EXPORT', state.LABELS, state.NAME);
			return;
		end;
		if isempty(state.LABELS), return; end;
		[fileName, pathName] = uiputfile([state.NAME '.lab'], 'Save labels as');
		if fileName == 0, return; end;		% cancelled
		fileName = [pathName, fileName];

% open the file
		[fid, msg] = fopen(fileName, 'wt');
		if fid == -1							
			error(sprintf('error attempting to open %s', fileName));
		end;

% write headers, data
		fprintf(fid, 'LABEL\tOFFSET\tNOTE\n');
		for i = 1 : length(state.LABELS),
			fprintf(fid, '%s\t%.1f\t', state.LABELS(i).NAME, state.LABELS(i).OFFSET);
			if ischar(state.LABELS(i).HOOK),
				fprintf(fid, '%s', state.LABELS(i).HOOK);
			end;
			fprintf(fid, '\n');
		end;

% clean up
		fclose(fid);
		fprintf('Labels written to %s\n', fileName);

		
%-----------------------------------------------------------------------------
% LEDSEL:  edit selected label

	case 'LEDSEL',
		cfgState = get(gcbf, 'userData');
		state = get(cfgState.GUI, 'userData');
		if gcbo == cfgState.LISTBOX & ~strcmp(get(gcbf, 'selectionType'), 'open'), 
			return;				% ignore single listbox clicks
		end;
		i = get(cfgState.LISTBOX, 'Value');	% index of label to edit
		if size(i,2) ~= 1, return; end;		% edit single selection only
		label = EditLabel(state.LABELS(i), 'Edit');
		if isempty(label), return; end;		% cancel
 		set(state.CURSORL, 'visible', 'off');
		delete(state.LABELS(i).HANDS);
%		axes(state.CURSORH);
		y = get(state.CURSORH, 'yLim');
		if isempty(state.LPROC),		% default plotting
			label = mview('LPLOT', label, y);
			set(label.HANDS(1), 'buttonDownFcn', 'mview(''LMOVE'',''DOWN'');');
		else,							% user proc
			label = feval(state.LPROC, state.LPSTATE, 'PLOT', label, y);
		end;
		set(state.CURSORL, 'visible', 'on');
		state.LABELS(i) = label;
		set(cfgState.GUI, 'userData', state);
		set(cfgState.LISTBOX, 'String', MakeList(state));
		
%-----------------------------------------------------------------------------
% LIMPORT:  default label import (import offsets from default format spreadsheet file)

	case 'LIMPORT',
		state = get(gcbf, 'userdata');
		[fileName, pathName] = uigetfile('*.lab', 'Load labels from');
		if fileName == 0, return; end;		% cancelled

		if ~isempty(state.LPROC) & nargin < 2,
			try,
				feval(state.LPROC, state.LPSTATE, 'IMPORT', fullfile(pathName,fileName));
			catch,
				fprintf('label import not supported for %s\n', state.LPROC);
			end;
			return;
		end;

		try,
			fid = fopen(fullfile(pathName, fileName),'rt');
			lines = {};
			while 1,
				lx = fgetl(fid);
				if ~ischar(lx), break; end;
				lines{end+1} = lx;
			end;
			fclose(fid);
			lx = regexp(lines{1},'(\w+)','tokens');
			if ~(strcmp(lx{1},'LABEL') && strcmp(lx{2},'OFFSET')),
				error('unrecognized format');
			end;
			lines(1) = [];
			for k = 1 : length(lines),
				q = regexp(lines{k},'(\w*)\s+([0-9.]+)','tokens');
				if isempty(q), continue; end;
				q = q{1};
				label = struct('NAME',q{1}, 'OFFSET',str2num(q{2}),'VALUE',[],'HOOK',[]);
				mview('MAKELBL',label,-1);
			end;
			fprintf('Labels imported from %s\n', fileName);
		catch,
			fprintf('error attempting to read labels from %s\n', fileName);
		end;

		
%-----------------------------------------------------------------------------
% LLOAD:  load labels from variable or mat file

	case 'LLOAD',
		name = GetName('', 'Load labels from...');
		if isempty(name) return; end;	% cancel

% first try to load variable from base workspace
		if evalin('base',sprintf('exist(''%s'')',name)),
			labels = evalin('base',name);

% then try mat file on search path
		elseif exist(sprintf('%s.mat',name)),
			labels = load(name,name);
			labels = labels.(name);
			name = which(sprintf('%s.mat',name));	
		else,
			fprintf('no variable or mat file matching %s found\n', name);
			return;
		end;
		if ~(isstruct(labels) && isfield(labels,'HOOK') && isfield(labels,'OFFSET')),
			fprintf('%s does not evaluate to a valid labels variable\n', name);
			return;
		end;		
		for k = 1 : length(labels),
			mview('MAKELBL',labels(k),-1);
		end;
		fprintf('labels loaded from %s\n', name);
	
%-----------------------------------------------------------------------------
% LMAKE:  menu-triggered label creation

	case 'LMAKE',
		state = get(gcbf, 'userdata');
		if isempty(state.LPROC),	% default labelling
			mview('MAKELBL');
		else,						% user proc labelling
			feval(state.LPROC, state.LPSTATE, 'DOWN', state.CURSOR, 1);
		end;

		
%-----------------------------------------------------------------------------
% LMOVE:  move existing label
%
%	varargin{3} may hold name of lproc caller for setting mouseUp handler
%	or if == -1 supporting double-click label editing only

	case 'LMOVE',
		state = get(gcbf, 'userdata');
		curPt = get(gca, 'currentPoint');
		x = curPt(1,1);
		switch varargin{2},
			case 'DOWN',
				for n = 1 : length(state.LABELS),		% find clicked label
					if state.LABELS(n).HANDS(1) == gcbo, break; end;
				end;
				
% double-click:  edit this label
				if strcmp(get(gcbf, 'selectionType'), 'open'),	
					fh = gcbf;
					label = EditLabel(state.LABELS(n), 'Edit', 1);
					if isempty(label), return; end;		% cancel
					
% handle label deletion
					if ~isstruct(label),				% (-1 flag)
					
% special handling for grouped labels:  must have VALUE field with {idString, group, ...}
						v = state.LABELS(n).VALUE;
						if ~isempty(v) && iscell(v) && length(v)>1 && ischar(v{1}),
							idString = v{1};
							group = v{2};
							idx = [];
							for k = 1 : length(state.LABELS),
								v = state.LABELS(k).VALUE;
								if isempty(v) || ~(iscell(v) && length(v)>1 && ischar(v{1}) && strcmp(idString,v{1})), continue; end;
								if v{2} == group,
									delete(state.LABELS(k).HANDS);
									idx(end+1) = k;
								end;
							end;
							state.LABELS(idx) = [];
							
% delete just this label						
						else,
							delete(state.LABELS(n).HANDS);
							state.LABELS(n) = [];
						end;
						set(fh, 'userData', state);
						return;
					end;
					set(state.CURSORL, 'visible', 'off');
					delete(state.LABELS(n).HANDS);
					axes(state.CURSORH);
					ylim = get(state.CURSORH, 'yLim');
					if isempty(state.LPROC),		% default plotting
						label = mview('LPLOT', label, ylim);
						set(label.HANDS(1), 'buttonDownFcn', 'mview(''LMOVE'',''DOWN'');');
					else,							% user proc
						label = feval(state.LPROC, state.LPSTATE, 'PLOT', label, ylim);
					end;
					set(state.CURSORL, 'visible', 'on');
					state.LABELS(n) = label;
					set(fh, 'userData', state);
					return;
				end;
				if nargin>2 && isequal(varargin{3},-1), return; end;		% label editing only
% else set up for move								
				set(state.CURSORF, 'string', sprintf(' %.1f', x));
				state.LPSTATE = struct('H',gcbo, 'IDX',n, 'SAVESTATE', state.LPSTATE);
				if length(varargin) > 2,
					upS = sprintf('%s([],''LMOVE'');',varargin{3});	% LPROC will handle mouseUp
				else,
					upS = 'mview(''LMOVE'',''UP'');';
				end;
				set(gcbf, 'windowButtonMotionFcn', 'mview(''LMOVE'',''MOVE'');', ...
							'windowButtonUpFcn',upS, ...
							'pointer', 'crosshair', 'userData',state);
			case 'MOVE',
				xlim = get(gca, 'xlim');
				ylim = get(gca, 'ylim');
				if x < xlim(1), x = xlim(1); end;
				if x > xlim(2), x = xlim(2); end;
				set(state.LPSTATE.H, 'xdata', [x x]);				% move label
				if length(state.LABELS(state.LPSTATE.IDX).HANDS)>1,	% move name
					h = state.LABELS(state.LPSTATE.IDX).HANDS(2);
					pos = get(h, 'position');
					pos(1) = x;
					set(h, 'position', pos);
				end;
				set(state.CURSORF, 'string', sprintf(' %.1f', x));
			case 'UP',
				state.LABELS(state.LPSTATE.IDX).OFFSET = x;
				state.LPSTATE = state.LPSTATE.SAVESTATE;
				set(gcbf, 'windowButtonMotionFcn', '', ...
					'windowButtonUpFcn', '', ...
					'pointer', 'arrow', 'userData', state);
				set(state.CURSORF, 'string', sprintf(' %.1f', state.CURSOR));
		end;

		
%-----------------------------------------------------------------------------
% LPLOT:  default label plotting (passed label, ylim)
%
%	returns updated label

	case 'LPLOT',
		if nargin > 3, fh = varargin{4}; else, fh = gcbf; end;
		state = get(fh, 'userdata');
		label = varargin{2};
		ylim = varargin{3} * .99;
		x = [label.OFFSET label.OFFSET];
		if isfield(label,'STYLE'),
			label.HANDS = xorline(x, ylim, 'tag', 'LABEL', label.STYLE{:});
		else,
			label.HANDS = xorline(x, ylim, 'tag', 'LABEL', 'color','y');
		end;
		if ~isempty(label.NAME),
			label.HANDS(end+1) = text(x(2), ylim(2), [' ', label.NAME], ...
				'tag', 'LABEL', ...
				'interpreter','none', ...
				'verticalAlignment', 'top', ...
				'fontname', 'geneva', ...
				'fontsize', 9);
		end;
		mOut = label;

		
%-----------------------------------------------------------------------------
% LSAVE:  save labels to workspace

	case 'LSAVE',
		state = get(gcbf, 'userdata');
		name = [state.NAME '_lbl'];
		if nargin < 2,
			name = GetName(name, 'Save labels as...');
			if isempty(name) return; end;	% cancel
		end;
		labels = rmfield(state.LABELS, 'HANDS');
		assignin('base', name, labels);
		evalin('base', name)				% for listing
		
		
%-----------------------------------------------------------------------------
% LSETPROC:  set labelling behavior

	case 'LSETPROC',
		state = get(gcbf, 'userdata');
		updateLabs = 0;
		switch varargin{2},
			case 0,			% clear user proc
				file = '<Default>';
				state.LPROC = [];
				state.LPSTATE = [];
			case 1,			% set user proc
				[file, p] = uigetfile([fileparts(which('mview')),filesep,'lp*.m'], 'Select labelling procedure');
				if file == 0, return; end; 	% cancelled
				i = findstr(file, '.');
				if ~isempty(i), file = file(1:i(1)-1); end;
				newState = feval(file, [], 'CONFIG');	% call user proc config handler (1st time)
				if isempty(newState), return; end;	% cancelled
				if iscell(newState),
					state.LPSTATE = newState{1};
					updateLabs = newState{2};
				else,
					state.LPSTATE = newState;
				end;
				state.LPROC = file;
				state.LPSTATE = newState;
			case 2,			% reconfigure
				file = state.LPROC;
				if isempty(file), mview('LCONFIG'); return; end;
				newState = feval(file, state.LPSTATE, 'CONFIG');	% call user proc config handler
				if isempty(newState), return; end;	% cancelled
				if iscell(newState),
					state.LPSTATE = newState{1};
					updateLabs = newState{2};
				else,
					state.LPSTATE = newState;
				end;
		end;
		set(state.LBLMENU, 'Label', file);
		if updateLabs,
			labels = state.LABELS;
			delete(cell2mat({labels.HANDS}));
			for li = 1 : length(labels),
				axes(state.CURSORH);
				ylim = get(state.CURSORH, 'ylim') * .99;
				labels(li) = feval(state.LPROC, state.LPSTATE, 'PLOT', labels(li), ylim, state.FH);
			end;
			set(cell2mat({labels.HANDS}),'visible','on');
			state.LABELS = labels;
		end;
		set(gcbf, 'userdata', state);

		
%-----------------------------------------------------------------------------
% LSETSEL:  set selection to label pair bracketing cursor

	case 'LSETSEL',
		state = get(gcbf, 'userdata');
		[h,t] = GetLblPair(state.LABELS, state.CURSOR);
		if isinf(h), return; end;
		state.HEAD = h;
		state.TAIL = t;
		set(gcbf, 'userData', state);
		SetBounds(state);
		
		
%-----------------------------------------------------------------------------
% MAKELBL:  make new label
%
% args(1) - action
% args(2) - label
% args(3) - interactive:  == -1, force silent
% args(4) - fh
%
%	returns mOut = index of created label; [] on cancel

	case 'MAKELBL',
		if nargin > 3, fh = varargin{4}; else, fh = gcbf; end;
		state = get(fh, 'userdata');
		if nargin < 2 | isempty(varargin{2}),				% create default label
			newLabel = struct('NAME', '', ...
							'OFFSET', state.CURSOR, ...
							'VALUE', [], ...
							'HOOK', '', 'HANDS', []);
		else,
			newLabel = varargin{2};	% user-supplied label
			if isempty(newLabel.OFFSET), newLabel.OFFSET = state.CURSOR; end;
			if isempty(newLabel.VALUE) & nargin>2, newLabel.VALUE = varargin{3}; end;
			newLabel.HANDS = [];
		end;
		if ~isfield(newLabel, 'STYLE'), newLabel.STYLE = {}; end;
		interactive = ~strcmp(state.MOVEMODE,'LBL_SILENT');
		if nargin > 2, interactive = (varargin{3} == 1); end;
		if interactive,				% annotate
			newLabel = EditLabel(newLabel, 'Create');
			if isempty(newLabel), 	% cancel
				state.MOVEMODE = '';
				set(gcbf, 'userdata', state);
				mOut = [];
				return; 
			end;	
		end;

		axes(state.CURSORH);
		y = get(state.CURSORH, 'yLim');
		set(state.CURSORL, 'visible', 'off');
		if isempty(state.LPROC),		% default plotting
			newLabel = mview('LPLOT', newLabel, y);
			set(newLabel.HANDS(1), 'buttonDownFcn', 'mview(''LMOVE'',''DOWN'');');
		else,							% user proc
			newLabel = feval(state.LPROC, state.LPSTATE, 'PLOT', newLabel, y, fh);
		end;
		set(state.CURSORL, 'visible', 'on');		
		
		state.MOVEMODE = '';
		if isempty(state.LABELS),
			state.LABELS = newLabel;
			mOut = 1;
		else,							% insert new label, ordered by offset
			offsets = cell2mat({state.LABELS.OFFSET});
			if newLabel.OFFSET < offsets(1),
				state.LABELS = [newLabel state.LABELS];
				mOut = 1;
			elseif newLabel.OFFSET > offsets(end),
				state.LABELS = [state.LABELS newLabel];
				mOut = length(state.LABELS);
			else,
				for i = 2 : length(state.LABELS),
					if newLabel.OFFSET < offsets(i), break; end;
				end;
% test for duplicate label
				if newLabel.OFFSET == offsets(i-1) && strcmp(newLabel.NAME,state.LABELS(i-1).NAME) && isequal(newLabel.VALUE,state.LABELS(i-1).VALUE),
					delete(newLabel.HANDS);
					mOut = [];
					set(fh, 'userdata', state);
					return;
				end;
				if ~isfield(state.LABELS,'STYLE'), for k = 1 : length(state.LABELS), state.LABELS(k).STYLE = {}; end; end
				state.LABELS = [state.LABELS(1:i-1) newLabel state.LABELS(i:end)];
				mOut = i - 1;
			end;
		end;
		set(fh, 'userdata', state);
		
		
%-----------------------------------------------------------------------------
% MOVECUR:  move cursor

	case 'MOVECUR',
		state = get(gcbf, 'userdata');
		xy = get(gca, 'currentPoint');
		x = xy(1,1);
		if x < state.HEAD, x = state.HEAD; end;
		if x > state.TAIL, x = state.TAIL; end; 
		c = get(state.CURSORL, 'xData');
		if x ~= c,
			state.CURSOR = x;
			set(gcbf, 'userData', state);
			SetCursor(state);
		end;

	
%-----------------------------------------------------------------------------
% MOVESEL:  move selection

	case 'MOVESEL',
		state = get(gcbf, 'userdata');
		xy = get(gca, 'currentPoint');
		x = xy(1,1); y = xy(1,2);
		switch state.MOVEMODE,
			case 'HEAD',
				if x < 0, x = 0; end;
				if x > state.TAIL-state.MINDUR, x = state.TAIL-state.MINDUR; end;
				state.HEAD = x;
			case 'TAIL',
				if x > state.DUR, x = state.DUR; end;
				if x < state.HEAD+state.MINDUR, x = state.HEAD+state.MINDUR; end;
				state.TAIL = x;
			otherwise,
				dx = x + state.MOVEMODE;
				if state.HEAD+dx < 0, dx = 0-state.HEAD; end;
				if state.TAIL+dx > state.DUR, dx = state.DUR-state.TAIL; end;
				state.HEAD = state.HEAD + dx;
				state.TAIL = state.TAIL + dx;
				state.MOVEMODE = -x;
		end;
		state.MOVED = 1;			% some movement occurred
		set(gcbf, 'userdata', state);
		SetBounds(state, 1);		% update selection bounds

		
%-----------------------------------------------------------------------------
% MOVESPAT:  move within spatial panel

	case 'MOVESPAT',
		state = get(gcbf, 'userdata');
		xy = get(gca, 'currentPoint');
		x = xy(1,1); y = xy(1,2);
		set(state.XF, 'string', sprintf(' %.1f',x));
		set(state.YF, 'string', sprintf(' %.1f',y));
		
		
%-----------------------------------------------------------------------------
% MOVESPEC:  move within spectrum panel

	case 'MOVESPEC',
		state = get(gcbf, 'userdata');
		xy = get(gca, 'currentPoint');
		x = xy(1,1); y = xy(1,2);
		set(state.XF, 'string', round(x));
		set(state.YF, 'string', sprintf(' %.1f',y));
		
		
%-----------------------------------------------------------------------------
% NUDGE:  step/shift cursor

	case 'NUDGE',
		state = get(gcbf, 'userdata');
		nudge = varargin{2};
		if abs(nudge) > 1,	% shift
			h = state.HEAD;
			t = state.TAIL;
			c = state.CURSOR;
			if c >= h && c <= t,
				c = c - h;
			else,
				c = 0;
			end;
			ht = t - h;
			if nudge < 0,
				h = h - ht;
				if h < 0, h = 0; end;
				t = h + ht;
			else,
				t = t + ht;
				if t > state.DUR, t = state.DUR; end;
				h = t - ht;
			end;
			state.CURSOR = c + h;
			state.HEAD = h;
			state.TAIL = t;
			set(gcbf, 'userdata', state);
			SetBounds(state,0);
		else,	% step
			c = state.CURSOR + state.NUDGE * nudge;	% msecs
			if c < state.HEAD,
				c = state.HEAD;
			elseif c > state.TAIL,
				c = state.TAIL;
			end;
			state.CURSOR = c;
			set(gcbf, 'userdata', state);
			SetCursor(state);
		end;

		
%-----------------------------------------------------------------------------
% PLAY:  audio output

	case 'PLAY',
		state = get(gcbf, 'userdata');
		hs = floor(state.HEAD*state.SRATE/1000)+1;	% msecs -> samps
		ts = floor(state.TAIL*state.SRATE/1000)+1;
		cs = floor(state.CURSOR*state.SRATE/1000)+1;
		ns = length(state.DATA(state.FI).SIGNAL);
		mode = varargin{2};
		mh = get(gcbo, 'userData');		% play submenu handles
		if mode < 7,
			for mi = 1 : length(mh)-1,	% last one is alternate track
				if mi == mode, as = 'P'; else, as = ''; end;
				set(mh(mi), 'accelerator', as);
			end;
			idx = state.FI;
		else,		% alternate track
			sr = cell2mat({state.DATA.SRATE});
			if sr(1) == sr(2),
				for mi = 1 : length(mh)-1,	% last one is alternate track
					if strcmp(get(mh(mi),'accelerator'),'P'), break; end;
				end;
				idx = 2;
				mode = mi;
			end;
		end
		
		switch mode,
			case 1, 	% selection
				;
			case 2, 	% file
				hs = 1; ts = ns;
			case 3, 	% to cursor
				if cs<hs, cs = hs; end; ts = cs;
			case 4, 	% from cursor
				if cs>ts, cs = ts; end; hs = cs;
			case 5, 	% 150ms centered on cursor
				t = floor(([-75 75]+state.CURSOR)*state.SRATE/1000)+1;
				if t(1) < 1, hs = 1; else, hs = t(1); end;
				if t(2) > ns, ts = ns; else, ts = t(2); end;
			case 6,		% between label pair bracketing cursor
				[h,t] = GetLblPair(state.LABELS,state.CURSOR);
				if ~isinf(h),
					hs = floor(h*state.SRATE/1000)+1;
					ts = floor(t*state.SRATE/1000)+1;
				end;
		end;

% want non-blocking audio output (audioplayer broken for R2011 versions)
% delete(PLAYER);clear PLAYER crashes
%		if ismac && ~verLessThan('matlab','8'),
			try,
				evalin('base','stop(PLAYER)');		% abort ongoing output
			catch,
				assignin('base','PLAYER', audioplayer(state.DATA(idx).SIGNAL(hs:ts) / abs(state.SPREAD), state.SRATE));
				evalin('base','set(PLAYER,''stopFcn'',''mview PLAYX'');play(PLAYER)');
				return;
			end
% 		else,
% 			soundsc(state.DATA(idx).SIGNAL(hs:ts), state.SRATE);
% 		end;

	case 'PLAYX',
		evalin('base','clear PLAYER');
		

%-----------------------------------------------------------------------------
% REPORT:  show info at cursor location
%
% args(2) - if state passed, called from GetVals

	case 'REPORT',
		if nargin < 2,
			state = get(gcbf, 'userdata');
		else,
			state = varargin{2};
		end;
		signal = state.DATA(state.FI).SIGNAL;
		
% compute F0
		F0 = ComputeF0wrapper(state);
		
% compute zero crossings, RMS for WSIZE centered on cursor
		ht = floor((state.CURSOR+[-state.WSIZE state.WSIZE]*.5)*state.SRATE/1000)+1;	% msecs -> samps
		if ht(1)<1, ht(1) = 1; end;
		if ht(2)>length(signal), ht(2) = length(signal); end;
		s = signal(ht(1):ht(2));
		zc = sum(abs(diff(s>=0)));
		rms = sqrt(mean(s.^2));
		
% compute formants
		[p,f,formants,bws,amps] = ComputeSpectra(state);
		if nargin > 1,
			mOut = {rms,zc,F0,formants};
			return;
		end;

% compute spectral center-of-gravity measures
		[L1, skew, kurt] = cog({signal, state.SRATE}, state.CURSOR);	

% get displayed values at cursor (skip audio)
		[vals,labs] = GetVals(state);

% report
		fprintf('\n%s:  cursor @ %.1f ms; selection is [%.1f %.1f] (%.1f) ms\n', ...
			state.NAME, state.CURSOR, state.HEAD, state.TAIL, state.TAIL-state.HEAD);
		fprintf('Window %.1f ms:  %d zero crossings, RMS = %.1f (%.1f dB), F0 = %d Hz, L1 = %.1f, skew = %.1f, kurt = %.1f\nFormants (BW):', ...
				state.WSIZE, zc, rms, 20*log10(rms), F0, L1, skew, kurt);
		nf = min([length(formants) state.NFMTS]);
		for fi = 1 : nf,
			fprintf('  F%d = %d (%d)', fi, formants(fi), bws(fi));
		end;
		fprintf('\nTraj: ');
		fprintf(' %6s',labs{:});
		fprintf('\nVals: ');
		fprintf(' %6.1f',vals);
		fprintf('\n');
					

%-----------------------------------------------------------------------------
% SAVECFG:  save current configuration to workspace

	case 'SAVECFG',
		state = get(gcbf, 'userdata');
		name = GetName([state.NAME '_cfg'], 'Save configuration as...');
		if isempty(name) return; end;		% cancel
		cfg = mview('GETCFG', state);
		assignin('base', name, cfg);
		evalin('base', name)		% for listing
		

%-----------------------------------------------------------------------------
% SAVESEL:  save currently visible selection to workspace (1)
% 			or everything but currently visible selection to workspace (2)

	case 'SAVESEL',
		state = get(gcbf, 'userdata');
		trim = (varargin{2} == 2);
		if trim, s = 'Save all but selection as...'; else, s = 'Save selection as...'; end
		name = GetName([state.NAME '_sel'], s);
		if isempty(name) return; end;		% cancel

% get visible components
		xi = 1;
		names = {state.DATA.NAME};
		tempMap = state.TEMPMAP;
		panels = state.TPANELS;
		nComps = {state.DATA.NCOMPS};
		for mi = 1 : length(tempMap),
			[ti,mod,comp,ac] = ParseTempMap(names, tempMap{mi}, nComps);
			if ti==0, continue; end;		% unmatched name

% monodimensional
			if nComps{ti}==1,
				switch mod,
					case 1,		% unmodified
						s = state.DATA(ti).SIGNAL; 
					case 2,		% spectrogram (ignore)
						continue;
					otherwise,	% modified (get signal from display)
						s = get(panels(mi).LH,'ydata')';
				end;

% multidimensional
			else,
				if mod > 1,
					if ac,
						s = state.DATA(ti).SIGNAL(:,7+(mod-2)*4);
					else,
						s = state.DATA(ti).SIGNAL(:,find(comp)+(mod-1)*4-1);
					end;
				else,
					k = [1 : 3];
					if mod > 1, k = k + (mod-2)*4 - 1; end;
					s = state.DATA(ti).SIGNAL(:,k);
					if ~ac, s = s(:,find(comp)); end;
				end;
			end;
			sr = panels(mi).SR;
			sn = tempMap{mi};
			sel(xi) = struct('NAME',sn,'SRATE',sr,'SIGNAL',s);
			xi = xi + 1;
		end;		

% handle trimming (save all but selection)
		if trim,
			if state.HEAD == 0 && state.TAIL == state.DUR,
				fprintf('nothing to save (all data selected)\n');
				return;
			end
			for ti = 1 : length(sel),
				hs = floor(state.HEAD*sel(ti).SRATE/1000)+1;
				ts = floor(state.TAIL*sel(ti).SRATE/1000)+1;
				if state.HEAD==0,
					sel(ti).SIGNAL = sel(ti).SIGNAL(ts:end,:);
				elseif state.TAIL==state.DUR,
					sel(ti).SIGNAL = sel(ti).SIGNAL(1:hs,:);
				else,
					sel(ti).SIGNAL = sel(ti).SIGNAL([1:hs,ts:end],:);
				end
			end;
			labels = state.LABELS;
			if ~isempty(labels),
				for li = length(labels) : -1 : 1,
					if labels(li).OFFSET > state.HEAD && labels(li).OFFSET < state.TAIL,
						labels(li) = [];
					elseif labels(li).OFFSET >= state.TAIL,
						labels(li).OFFSET = labels(li).OFFSET - (state.TAIL - state.HEAD);
						labels(li).VALUE = [];
						labels(li).HANDS = [];
					end;
				end;
				sel(1).LABELS = labels;
			end;
			sel(1).SOURCE = struct('NAME',state.NAME,'HEAD',state.HEAD,'TAIL',state.TAIL);
			fprintf('Trimmed selection %s removed %.1f : %.1f (%.1f) ms\n', ...
				name, state.HEAD, state.TAIL, state.TAIL-state.HEAD);		

% save selection:  adjust offsets to start of selection
		else,
			for ti = 1 : length(sel),
				hs = floor(state.HEAD*sel(ti).SRATE/1000)+1;
				ts = floor(state.TAIL*sel(ti).SRATE/1000)+1;
				sel(ti).SIGNAL = sel(ti).SIGNAL(hs:ts,:);
			end;
			labels = state.LABELS;
			if ~isempty(labels),
				for li = length(labels) : -1 : 1,
					if labels(li).OFFSET < state.HEAD | labels(li).OFFSET > state.TAIL,
						labels(li) = [];
					else,
						labels(li).OFFSET = labels(li).OFFSET - state.HEAD;
						labels(li).VALUE = [];
						labels(li).HANDS = [];
					end;
				end;
				sel(1).LABELS = labels;
			end;
			sel(1).SOURCE = struct('NAME',state.NAME,'HEAD',state.HEAD,'TAIL',state.TAIL);
			fprintf('Saved selection %s is %.1f : %.1f (%.1f) ms\n', ...
				name, state.HEAD, state.TAIL, state.TAIL-state.HEAD);
		end;
		assignin('base', name, sel);
		evalin('base', name)		% for listing
		
	
%-----------------------------------------------------------------------------
% SELCHG:  selection change

	case 'SELCHG',
		state = get(gcbf, 'userdata');
		switch varargin{2},
			case -1, 		% set head from cursor
				head = state.CURSOR;
				if head >= state.TAIL, head = state.TAIL-state.MINDUR; end;
				state.HEAD = head;
			case -2, 		% set tail from cursor
				tail = state.CURSOR;
				if tail <= state.HEAD, tail = state.HEAD+state.MINDUR; end;
				state.TAIL = tail;
			case -3,		% shrink selection
				nudge = .1 * (state.TAIL - state.HEAD);
				head = state.HEAD + nudge;
				if head >= state.TAIL,
					head = state.TAIL-1;
					tail = state.TAIL;
				else,
					tail = state.TAIL - nudge;
					if tail <= head, tail = head+state.MINDUR; end;
				end;
				state.HEAD = head;
				state.TAIL = tail;
			case -4,		% expand selection
				nudge = .1 * (state.TAIL - state.HEAD);
				head = state.HEAD - nudge;
				if head < 0, head = 0; end;
				tail = state.TAIL + nudge;
				if tail > state.DUR, tail = state.DUR; end;
				if state.HEAD==head & state.TAIL==tail, return; end;
				state.HEAD = head;
				state.TAIL = tail;
			case -5,		% shift selection left
				selLen = state.TAIL - state.HEAD;
				head = state.HEAD - selLen;
				if head < 0, head = 0; end
				state.HEAD = head;
				state.TAIL = head + selLen;
			case -6,		% shift selection right
				selLen = state.TAIL - state.HEAD;
				tail = state.TAIL + selLen;
				if tail > state.DUR, tail = state.DUR; end
				state.HEAD = tail - selLen;
				state.TAIL = tail;
			case 0, 		% reset full selection
				state.HEAD = 0;
				state.TAIL = state.DUR;
			case 1,			% head changed
				head = str2num(get(state.HEADF, 'string'));
				if isempty(head),
					head = get(state.HEADF, 'string');
					head = str2num(head(find(head>='0')));
					if isempty(head), head = state.HEAD; end;
				end;
				if head<0, head = 0; end;
				if head >= state.TAIL, head = state.TAIL-state.MINDUR; end;
				state.HEAD = head;
			case 2,			% tail changed
				tail = str2num(get(state.TAILF, 'string'));
				if isempty(tail),
					tail = get(state.TAILF, 'string');
					tail = str2num(tail(find(tail>='0')));
					if isempty(tail), tail = state.TAIL; end;
				end;
				if tail <= state.HEAD, tail = state.HEAD+state.MINDUR; end;
				if tail > state.DUR, tail = state.DUR; end;
				state.TAIL = tail;
		end;
		set(gcbf, 'userData', state);
		SetBounds(state);


%-----------------------------------------------------------------------------
% SETSCALING:  set common scaling

	case 'SETSCALING',
		state = get(gcbf, 'userdata');
		spreads = state.SPREADS;
		width = 300;
		height = 100;
		pos = CenteredDialog(gcbf, width, height);
		
		cfg = dialog('Name', 'Set Common Scaling', ...
			'Tag', 'MVIEW', ...
			'menubar', 'none', ...
			'Position', pos, ...
			'UserData', 0);

		uicontrol(cfg, ...
			'Position', [15 60 20 18], ...
			'Style', 'text', ...
			'HorizontalAlignment', 'right', ...
			'String', 'Mvt');
		mh = uicontrol(cfg, ...
			'Position', [40 60 60 20], ...
			'Style', 'edit', ...
			'HorizontalAlignment', 'left', ...
			'String', sprintf(' %.2f',spreads(1)));
		
		uicontrol(cfg, ...
			'Position', [105 60 20 18], ...
			'Style', 'text', ...
			'HorizontalAlignment', 'right', ...
			'String', 'Vel');
		vh = uicontrol(cfg, ...
			'Position', [130 60 60 20], ...
			'Style', 'edit', ...
			'HorizontalAlignment', 'left', ...
			'String', sprintf(' %.2f',spreads(2)));
		
		uicontrol(cfg, ...
			'Position', [195 60 20 18], ...
			'Style', 'text', ...
			'HorizontalAlignment', 'right', ...
			'String', 'Acc');
		ah = uicontrol(cfg, ...
			'Position', [220 60 60 20], ...
			'Style', 'edit', ...
			'HorizontalAlignment', 'left', ...
			'String', sprintf(' %.2f',spreads(3)));
		
% OK, cancel buttons
		uicontrol(cfg, ...		% buttons
			'Position',[width/2-70 15 60 25], ...
			'String','OK', ...
			'Callback','set(gcbf,''UserData'',1);uiresume');
		uicontrol(cfg, ...
			'Position',[width/2+10 15 60 25], ...
			'String','Cancel', ...
			'Callback','uiresume');
		
% wait for input
		uiwait(cfg);
		if get(cfg, 'UserData'),
			m = str2num(get(mh, 'string')); if isempty(m), m = spreads(1); end;
			v = str2num(get(vh, 'string')); if isempty(v), v = spreads(2); end;
			a = str2num(get(ah, 'string')); if isempty(a), a = spreads(3); end;
			delete(cfg);
			state.SPREADS = [m v a];
			panDims = get(state.CURSORH, 'position');
			try,
				delete(state.TPANELS.AXIS);
			catch,
				for k = 1 : length(state.TPANELS), delete(state.TPANELS(k).AXIS); end;
			end;
			[state.TPANELS,state.SPECGRAM] = InitTraj(state.DATA, state.DUR, panDims, state.SPREADS, state.TEMPMAP);
			set(gcbf, 'userdata', state);
			SetBounds(state, 3);
		else,
			delete(cfg);
		end;
		
	
%-----------------------------------------------------------------------------
% SPATPLOT:  spatial trace

	case 'SPATPLOT',
		if strcmp(varargin{2},'CLEAR'),
			delete(findobj(gca, 'tag', 'TRACE'));
			return;
		end;
		fh = gcbf;
		if isempty(fh),
			set(0,'ShowHiddenHandles', 'on');
			fh = findobj('Tag', 'MVIEW');
			fh = fh(1);
		end;
		state = get(fh, 'userdata');

% rotate3D handlers
		if strcmp(varargin{2},'VIEW'),
			switch varargin{3},
				case 2, view(state.SPATIALA,2); box on;
				case 3, view(state.SPATIALA,[0,0]); box on;
				case 4, view(state.SPATIALA,[-90,0]); box on;
				case 5, view(state.SPATIALA,[-110,-18]); box off;
				case 6, view(state.SPATIALA,3); box off;
				case 7, view(state.SPATIALA,[27,20]); box off;
				case 'GET',		% get view directly
					opt = struct('Resize','on','WindowStyle','modal','interpreter','none');
					[az,el] = view(state.SPATIALA);
					q = inputdlg({'AZ: ','EL: '},'Specify View',1,{num2str(az),num2str(el)});
					if ~isempty(q), 
						view(state.SPATIALA,[str2num(q{1}),str2num(q{2})]);
					end;
					box off;
				case 'ROT', 		% free rotate
					if strcmpi(get(gcbo,'checked'),'off'),
						set(gcbo,'checked','on');
						rotate3d(state.SPATIALA);
						return;
					end;
					rotate3d off;
					set(gcbo,'checked','off');
			end;
			[az,el] = view(state.SPATIALA);
			state.VIEW = [az,el];
			set(gcbf, 'userData', state);
			return;
		end;

% history
		map = hsv(64);
		for ti = state.SPATCHAN,
			hts = floor([state.HEAD state.TAIL]*state.DATA(ti).SRATE/1000)+1;	% msecs -> samps		
			s = state.DATA(ti).SIGNAL(hts(1):hts(2),:);
			switch varargin{2},
				case 'HUE',
					ci = round(linspace(1,length(map),length(s)));
					h = 1;
					while h < length(s),
						t = find(ci == ci(h));
						if isempty(t), break; end;
						t = t(end);
						if h == t, t = h + 1; end;
						if state.IS3D,
							line(s(h:t,1), s(h:t,2), s(h:t,3), 'color', map(ci(h),:), 'tag', 'TRACE');
						else,
							line(s(h:t,1), s(h:t,2), 'color', map(ci(h),:), 'tag', 'TRACE');
						end;
						h = t;
					end;
				case 'HISTORY',
					if state.IS3D,
						line(s(:,1), s(:,2), s(:,3), 'color', state.DATA(ti).COLOR, 'tag', 'TRACE');
					else,
						line(s(:,1), s(:,2), 'color', state.DATA(ti).COLOR, 'tag', 'TRACE');
					end;
			end;
		end;
		if isempty(gcbf), set(0,'ShowHiddenHandles', 'off'); end;
		if isempty(state.CONTOURS), return; end;
		
% contours
% delay holds offset of 1st US frame w.r.t. EMA in secs 
%  >0: US starts after EMA; <0 US starts before EMA
		c = state.CONTOURS;
		[nPts,~,nc] = size(c);
		fps = state.DATA(1).SOURCE.FPS;
		delay = state.DATA(1).SOURCE.DELAY;
		ct = [0:nc-1]./fps - delay;		% contour timings w.r.t. EMA (secs)
		[~,hi] = min(abs(ct-state.HEAD/1000));		% contour indices
		if hi < 1, hi = 1; end;
		[~,ti] = min(abs(ct-state.TAIL/1000));
		if ti > nc, ti = nc; end;
		idx = [hi:ti];
		if length(idx) > 50, idx = round(linspace(hi,ti,50)); end;	% don't show more than 50 contours
		h=pp3(c(:,:,idx),'tag','TRACE');
		view(state.VIEW);
		uistack(h,'bottom');
		
		
%-----------------------------------------------------------------------------
% TRACKFMTS:  track formants

	case 'TRACKFMTS',
		state = get(gcbf, 'userdata');
		s = get(gcbo,'checked');
		state.FMTS = strcmp(s,'off');
		set(gcbf, 'userdata', state);
		if state.FMTS, s = 'on'; else, s = 'off'; end;
		set(state.FMTSMENU, 'checked', s);
		SetBounds(state, 0);
% 		ht = floor([state.HEAD,state.TAIL]*state.SRATE/1000)+1;
% 		params = evalin('base','TrackFmtsParams','{}');
% 		TrackFmts(state.DATA(state.FI).SIGNAL(ht(1):ht(2)), state.SRATE, params{:});
		
		
%-----------------------------------------------------------------------------
% UP:  handle mouseUp (complete move-in-progress)

	case 'UP',
		state = get(gcbf, 'userdata');
		set(gcbf, 'windowButtonMotionFcn', '', ...
			'windowButtonUpFcn', '');
		xy = get(gca, 'currentPoint');
		x = xy(1,1); y = xy(1,2);
		switch state.MOVEMODE,
			case {'CURSOR','LBL_SILENT','LBL_NOISY'},
				set(state.XF, 'string', '');
				set(state.YF, 'string', '');
				set(state.ZF, 'string', '');
				set(state.XFL, 'string', 'X');
				set(state.CURSORFL, 'string', 'Cursor ');
				state.CLICKINFO = [];
				if state.CURSOR == x | x < state.HEAD | x > state.TAIL, 
					set(gcbf, 'userData', state);
				else,
					c = get(state.CURSORL, 'xData');
					if x ~= c,
						state.CURSOR = x;
						set(gcbf, 'userData', state);
						SetCursor(state);
					else,
						set(gcbf, 'userData', state);
					end;
				end;
				if isempty(state.LPROC) & strncmp(state.MOVEMODE, 'LBL', 3),
					mview('MAKELBL'); 				% create new label
				end;
			case 'SPATIAL',
				set(state.XF, 'string', '');
				set(state.YF, 'string', '');
			case 'SPECTRA',
				set(state.XF, 'string', '');
				set(state.YF, 'string', '');
				set(state.XFL, 'string', 'X');
				set(state.YFL, 'string', 'Y');
			otherwise,
				if state.MOVED == 0, return; end;		% double-click within selection
				SetBounds(state);						% update selection bounds
		end;

		
%-----------------------------------------------------------------------------
% VARLIST:  init new mview viewer from varlist selection
%
%	arg:  -1 previous
%		   1 next
%		   0 menu selected
%
% if viewer of that name already open just pop it

	case 'VARLIST',
		state = get(gcbf, 'userdata');
		switch varargin{2},
			case -1, i = state.VLISTSEL - 1;
			case 1, i = state.VLISTSEL + 1;
			case 0, i = get(gcbo, 'userdata');
		end;
		if i < 1, return; end;
		if i > length(state.VLIST), return; end;
		name = state.VLIST{i};
		set(0,'ShowHiddenHandles', 'on');
		h = findobj('Tag', 'MVIEW');
		wList = [];
		for j = 1 : length(h),
			fn = get(h(j), 'name');
			wList{end+1} = fn(9:end);
		end;
		j = strmatch(name, wList, 'exact');		% test open viewers
		if ~isempty(j), figure(h(j)); end
		set(0,'ShowHiddenHandles', 'off');
		if isempty(j),							% open new viewer
			cfg = mview('GETCFG', state);
			cfg.FIGPOS = [];		% use default position
			mview(state.VLIST{i}, 'CONFIG', cfg, ...
						'VLIST', state.VLIST, 'VLSEL', i, ...
						'HEAD', state.HEAD, 'TAIL', state.TAIL);
		end;

		
%-----------------------------------------------------------------------------
% VIEW:  set view from command line

	case 'VIEW',
		set(0,'ShowHiddenHandles', 'on');
		fh = findobj('Tag', 'MVIEW');
		set(0,'ShowHiddenHandles', 'off');
		fh = fh(1);
		view(fh.UserData.SPATIALA, varargin{2});

		
%-----------------------------------------------------------------------------
% UPDATE:  manual update

	case 'UPDATE',
		state = get(gcbf, 'userdata');
		SetBounds(state, 0);

		
%-----------------------------------------------------------------------------
% ZOOM:  adjust zoomed window width

	case 'ZOOM',
		state = get(gcbf, 'userdata');
		za = get(state.ZOOM, 'userData');
		if nargin > 1	
			if varargin{2} == 0,		% plot in new figure
				fh = colordef('new', 'black');
				s = get(state.ZOOM,'ydata');
				plot(s,'w');
				ns = length(s);
				line(round(ns/2)*[1 1],get(gca,'ylim'),'color','g','linestyle',':');
				set(gca, 'xticklabel',[], 'xlim', [1 ns]);
				xlabel(sprintf('%g msecs', state.ZOOMW));
				ls = sprintf('Cursor:  %.1f msecs', state.CURSOR);
				title(ls);
				set(fh,'name',ls,'visible','on');
				return;
			else,	% get value from arg
				state.ZOOMW = varargin{2};
				set(get(za, 'userData'), 'value', state.ZOOMW);	% update slider pos
			end;
		else,		% get value from slider
			state.ZOOMW = round(get(gcbo, 'value'));
		end;
		set(gcbf, 'userdata', state);
		ns = round(state.ZOOMW/1000*state.SRATE);
		set(za, 'xlim', [1 ns]);
		set(findobj(za, 'tag', 'CURSOR'), 'xdata', round(ns/2)*[1 1]);	% center line
		set(get(za, 'xlabel'), 'string', sprintf('%g msecs', state.ZOOMW));
		SetCursor(state, 1);
		
		
%-----------------------------------------------------------------------------
% UNRECOGNIZED ACTION:  handle "mview <data>" form

	otherwise,
		if evalin('base', ['exist(''' varargin{1} ''',''var'')']),
			if nargin > 1,
				vName = varargin{1};
				data = evalin('base', vName);
				if ~isfield(data,'SIGNAL'),
					fprintf('%s does not have SIGNAL data (skipped)\n', vName);
					return;
				end
				eval([vName '=data;clear data;varargin{1}=' vName ';']);
				mview(varargin{:});				
			else,
				evalin('base',['mview(' varargin{1} ');']);
			end;
		else,
			vName = varargin{1};
			if findstr(vName, '*'),		% handle wildcarding
				vl = evalin('base',['who(''' vName ''')']);		% workspace first
				while ~isempty(vl),
					vn = vl{1};
					data = evalin('base',vn);
					isValid = isfield(data, 'SIGNAL');
					clear data;
					if isValid, break; end;
					fprintf('%s does not have SIGNAL data (skipped)\n', vn);
					vl(1) = [];
				end;
				fl = dir([vName '.mat']);						% then cwd mat files
				fl = {fl.name}';
				for i = 1 : length(fl), fl(i) = {fl{i}(1:end-4)}; end;	% kill '.mat'
				fl = [vl(:) ; fl(:)];
				if isempty(fl),
					error(['Error:  no variables or files matching ' vName ' found']);
				else,
					mview(fl, varargin{2:end});
					return;
				end;
			end;
			if isempty(which([vName '.mat'])),
				error(['Error:  variable ' vName ' not available on current path']);
			end;
			data = load(vName);

% if data holds variables named CFG, PAL, PHA, or LABELS they are loaded
			fn = char(fieldnames(data));
			if ~isempty(strmatch('cfg',fn,'exact')),
				varargin{end+1} = 'CONFIG';
				varargin{end+1} = data.cfg;
			end;
			if ~isempty(strmatch('pal',fn,'exact')),
				varargin{end+1} = 'PALATE';
				varargin{end+1} = double(data.pal);
			end;
			if ~isempty(strmatch('pha',fn,'exact')),
				varargin{end+1} = 'PHARYNX';
				varargin{end+1} = double(data.pha);
			end;				
			if ~isempty(strmatch('labels',fn,'exact')),
				varargin{end+1} = 'LABELS';
				varargin{end+1} = data.labels;
			end;				
			varargin{end+1} = 'NAME';
			varargin{end+1} = vName;
			eval([vName '=data.' vName ';clear data;varargin{1}=' vName ';'], ...
				['error([''' varargin{end} '.mat does not hold a variable of that name'']);']);
			mview(varargin{:});
		end;
		
end;


%=============================================================================
% PARSEDATA  - initialize input dataset
%
%	usage:  [data,spatChan,dur,minDur,spreads,range,is3D] = ParseData(data);
%
% computes velocity and accelaration for movement data, sets common scaling
%
% input:  data.SIGNAL [nSamps x nComps]
% output: data.SIGNAL [nSamps x X,Y,(Z) , vX,vY,(vZ),V , aX,aY,(aZ),A]
%
% Z ignored (as tilt) if unspecified or is3D zero, but placeholder columns inserted
% V is velocity magnitude (across all components)
% A is acceleration magnitude
%
% Velocity is computed by central difference, cm/sec units
% Acceleration is computed by central difference of velocity after
% 	smoothing with a 5 sample moving average filter (cm/sec^2 units)
%
% adds fields (if necessary)
%	data.SPREAD  data range [min , max]
%	data.NCOMPS  number of available components this trajectory
%	data.ANGLES  angles, RMS data
%
% also returns 
%	SPATCHAN - movement channel indices within data
%	DUR		 - duration of shortest concurrent signal
%	MINDUR	 - smallest display duration (1/minSR)
%	SPREADS	 - common scaling for movement, velocity, acceleration
%	RANGE	 - spatial range across all movement trajectories
%	IS3D	 - nonzero if true (non-tilt) data detected as 3rd component of movement

function [data,spatChan,dur,minDur,spreads,range,is3D,audioSpread] = ParseData(data,audioSpread,spatex);

is3D = 0;
range = [];
spreads = [0 , 0 , 0];			% movement, velocity, acceleration
dur = 1000*(length(data(1).SIGNAL)-1)/data(1).SRATE;	% clip to shortest signal of concurrent set
spatChan = zeros(1,length(data));
minSR = data(1).SRATE;

if isempty(strmatch('SPREAD', char(fieldnames(data)), 'exact')),
	data(1).SPREAD = [];					% add data range field
end;
if isempty(strmatch('NCOMPS', char(fieldnames(data)), 'exact')),
	data(1).NCOMPS = [];					% add # components field
end;
if isempty(strmatch('ANGLES', char(fieldnames(data)), 'exact')),
	data(1).ANGLES = [];					% add angles, RMS field
	gotAngles = 0;
else,
	gotAngles = 1;
end;

% get common scaling for movement; find shortest signal of concurrent dataset
for ti = 1 : length(data),
	data(ti).SIGNAL = double(data(ti).SIGNAL);	% support single precision data
	if ~isreal(data(ti).SIGNAL),
		fprintf('Warning:  complex data found in %s\n', data(ti).NAME);
		data(ti).SIGNAL = real(data(ti).SIGNAL);
	end;
	k = findstr(data(ti).NAME,'_');
	data(ti).NAME(k) = [];				% "_" not permitted in trajectory names
	[nSamps,nComps] = size(data(ti).SIGNAL);
	if nComps > 3, 
		nComps = 3;
		data(ti).ANGLES = data(ti).SIGNAL(:,4:end);
		gotAngles = 1;
	end;
	data(ti).NAME = upper(data(ti).NAME);
	if isempty(data(ti).NCOMPS), data(ti).NCOMPS = nComps; else, nComps = data(ti).NCOMPS; end;
	sr = data(ti).SRATE;
	if sr < minSR, minSR = sr; end;
	ts = floor(dur*sr/1000)+1;
	if ts > length(data(ti).SIGNAL), 
		ts = length(data(ti).SIGNAL);
	end;
	t = 1000*(ts-1)/sr;
	if t < dur, dur = t; end;
	if nComps > 1 && nComps <= 3 && sr < 2000,
		if isempty(range), range = repmat([inf;-inf],1,nComps); end;
		maxD = max(data(ti).SIGNAL(:,1:nComps));
		minD = min(data(ti).SIGNAL(:,1:nComps));
		incChan = 1;
		if ~isempty(spatex),		% this supports wildcarding
			if isempty(strmatch(data(ti).NAME,spatex,'exact'))
				for si = 1 : length(spatex),
					k = findstr(spatex{si},'*');
					if isempty(k), continue; end;
					q = regexp(data(ti).NAME,regexptranslate('wildcard',spatex{si}),'match');
					if isempty(q), continue; end;
					incChan = 0;
					break;
				end;
			else,
				incChan = 0;
			end;
		end;
		if incChan,
			range(1,:) = min([range(1,:) ; minD]);
			range(2,:) = max([range(2,:) ; maxD]);
			spatChan(ti) = ti;
		end;
		s = max(maxD - minD);
		data(ti).SPREAD = [-s s];
		if s > spreads(1), spreads(1) = s; end;
		if ~is3D & length(maxD)>2,			% test for true 3rd component (not tilt)
%			s = abs(data(ti).SIGNAL(:,3));
%			if max(s)-min(s) > 2,
				is3D = 1;
%			end;
		end;
	elseif isempty(data(ti).SPREAD),
		ds = max(abs(data(ti).SIGNAL));
		if data(ti).SRATE<5000 | ti>1,	% assume physiological data below 5kHz sampling rate, audio 1st data entry
			ds = [min(data(ti).SIGNAL);max(data(ti).SIGNAL)];
			ds = [-1;1] * .1*diff(ds) + ds;
		elseif isempty(audioSpread),		
			if ds <= 1,			% +/-1; scaled
				;
			elseif ds < 2048,	% 12 bit
				ds = 2048;
			elseif ds < 32768,	% 16 bit
				ds = 32768;
			else,				% >16 bit; scaled
				;
			end;
			audioSpread = ds;
		elseif audioSpread < 0,	% auto scaled
			audioSpread = -ds;
		else,					% specified
			ds = audioSpread;
		end;
		if length(ds) == 1, ds = [-ds ds]; end;
		data(ti).SPREAD = ds;
	end;
end;
spatChan = spatChan(find(spatChan));		% movement channel indices within data
minDur = ceil(1/minSR);						% min displayed duration
if ~is3D,
	for ti = spatChan,
		data(ti).NCOMPS = 2;				% disregard tilt
	end;
end;

if ~isempty(spatChan) & size(data(spatChan(1)).SIGNAL,2) == 11, 	% if derived signals already present (exported selection)
	for ti = spatChan,						% get common scaling for vel, acc
		td = data(ti).SIGNAL;
		s = max(max(td(:,4:7)) - min(td(:,4:7)));
		if s > spreads(2),
			spreads(2) = s;
		end;		
		s = max(max(td(:,8:11)) - min(td(:,8:11)));
		if s > spreads(3),
			spreads(3) = s;
		end;
	end;
	return;
end;

% compute derived signals
for ti = 1 : length(data),
	nComps = data(ti).NCOMPS;
	if nComps > 1,
		td = zeros(size(data(ti).SIGNAL,1),11);
	
% X, Y, (Z)
		td(:,1:nComps) = data(ti).SIGNAL(:,1:nComps);	

% vX, vY, (vZ), V (cm/sec)
		for ci = 4 : 6,
			td(:,ci) = data(ti).SRATE * [diff(td([1 3],ci-3)) ; (td(3:end,ci-3) - td(1:end-2,ci-3)) ; diff(td([end-2 end],ci-3))] ./ 20;	% central difference
			if ci==5 & ~is3D, break; end;
		end;
		td(:,7) = sqrt(sum(td(:,4:ci).^2,2));		% velocity magnitude (tangential velocity)
		s = max(max(td(:,4:7)) - min(td(:,4:7)));
		if s > spreads(2),
			spreads(2) = s;
		end;
	
% aX, aY, A (cm/sec^2)
% 		b = ones(1,5) / 5;					% 5 sample rectangular window moving average filter
% 		v = filtfilt(b,1,td(:,4:ci));		% filtered velocities	
		v = td(:,4:ci);
		for ci = 8 : 10,
			td(:,ci) = data(ti).SRATE * [diff(v([1 3],ci-7)) ; v(3:end,ci-7) - v(1:end-2,ci-7) ; diff(v([end-2 end],ci-7))] / 2;
			if ci==9 & ~is3D, break; end;
		end;
%		td(:,11) = sqrt(sum(td(:,8:ci).^2,2));		% acceleration magnitude
%		v = filtfilt(b,1,td(:,7));
		v = td(:,7);
		td(:,11) = abs(data(ti).SRATE * [v(3)-v(1) ; v(3:end)-v(1:end-2) ; v(end)-v(end-2)] / 2);
		s = max(max(td(:,8:11)) - min(td(:,8:11)));
		if s > spreads(3),
			spreads(3) = s;
		end;
	
		data(ti).SIGNAL = td;
	end;
end;
if ~gotAngles,
	data = rmfield(data, 'ANGLES');
end;


%=============================================================================
% CENTEREDDIALOG  - center a dialog on current figure
%
% returns POS [x , y, width, height] needed to center
% a dialog of WIDTH and HEIGHT pixels on figure FH

function pos = CenteredDialog(fh, width, height)

units = get(fh, 'units');
if strcmpi(units,'pixels'),
	units = [];
else,
	set(fh, 'units','pixels');
end;	
fPos = get(fh, 'position');
if ~isempty(units), set(fh, 'units',units); end;
pos = [fPos(1)+(fPos(3)-width)/2 , fPos(2)+(fPos(4)-height)/2 , width , height];


%=============================================================================
% COMPUTESPECTRA  - compute spectral cross-section at specified offset
%
% returns spectral power, frequency

function [p,f,formants,bandwidths,amplitudes] = ComputeSpectra(state)

%	get analysis frame

c = floor(state.CURSOR*state.SRATE/1000)+1;			% msecs->samples
ns = round(state.WSIZE/1000*state.SRATE);			% frame (msecs->samples)
h = c - round(ns/2);
if h < 1, h = 1; end;
t = h + ns - 1;
signal = state.DATA(state.FI).SIGNAL;
if t > length(signal),
	t = length(signal);
	h = t - ns + 1;
end;
signal = signal(h:t);

% 	pre-emphasize, window, lpc

signal = hanning(ns).*preemp(signal, state.PREEMP);
R = flipud(fftfilt(conj(signal),flipud(signal)));	% unbiased autocorrelation estimate
a = levinson(R, state.ORDER);						% LPC
g = sqrt(real(sum((a').*R(1:state.ORDER+1,:))));	% gain
[p,f] = freqz(g, a, 256, state.SRATE);
p = 20*log10(abs(p/state.SOFF+eps)');

%	find formants

if nargout > 2,
	r = flipud(sort(roots(a)));
	formants = angle(r(find(imag(r) > 0)))' * state.SRATE/(2*pi);
	bandwidths = -log(abs(r(find(imag(r) > 0))))' * state.SRATE/pi;
	[formants, idx] = sort(formants);
	bandwidths = bandwidths(idx);
	idx = find(bandwidths<400);				% discard peaks with >= bwclip Hz bw
	formants = round(formants(idx));
	bandwidths = round(bandwidths(idx));
	if isempty(formants),
		formants = NaN;
		bandwidths = NaN;
	else,
		while ~formants(1),					% kill initial 0s
			formants = formants(2:end);
			bandwidths = bandwidths(2:end);
		end;
		n = min(length(formants), 5);
		formants = formants(1:n);	
		bandwidths = bandwidths(1:n);
	end;
	if isnan(formants),
		amplitudes = NaN;
	else,
		amplitudes = interp1(f, p, formants, '*linear');
	end;	
end;


%=============================================================================
% COMPUTEF0WRAPPER  - computes pitch for three 40 msec buffers centered on cursor (M&G heuristic)
%
%	usage:  F0 = ComputeF0wrapper(state)
%
%
% COMPUTEF0local  - modified autocorrelation pitch estimator
%
%	usage:  F0 = ComputeF0local(s, sr)
%
% Computes pitch estimation based on the filtered error signal autocorrelation 
% sequence to minimize formant interaction (modified autocorrelation analysis)
%
% S is a vector of speech sampled at SR Hz
% returns F0 (Hz) and normalized amplitude
%
% cf. Markel & Gray (1976) Linear Prediction of Speech, pp. 203-206
%

function F0 = ComputeF0wrapper(state)

signal = state.DATA(state.FI).SIGNAL;
c = floor(state.CURSOR*state.SRATE/1000)+1;			% msecs->samples
ns = round(40/1000*state.SRATE);					% frame (40 msecs->samples)
F0 = zeros(1,3);
v = F0; 
for fi = 1 : 3,										% compute for 3 buffers centered on cursor
	h = c - round(ns/2)*(3-fi);
	if h < 1, h = 1; end;
	t = h + ns - 1;
	if t > length(signal),
		t = length(signal);
		h = t - ns + 1;
	end;
	[F0(fi),v,R] = ComputeF0local(signal(h:t), state.SRATE, state.ISF);
end;
if length(find(F0)) < 2,			% if any two buffers 0
	F0 = NaN;							% bogus
elseif std(F0(find(F0))) > 15,		% if std dev > 15 Hz
	F0 = F0(find(F0));
	if min(F0) < .67*max(F0),			% check for pitch doubling
		F0 = min(F0);
	else,
		F0 = NaN;
	end;
elseif F0(2),						% center result available
	F0 = F0(2);							% cursor-centered result
else,								% otherwise
	F0 = mean(F0(find(F0)));			% mean of non-zero results
end;


function [F0,v,R] = ComputeF0local(s, sr, isF);

F0 = 0;
order = 12;
thresh = .4;

% lowpass filter (800 Hz)
% s = s(:);
ns = length(s);
[b,a] = cheby2(6,30,1600/sr);
s = filtfilt(b, a, s);

% compute inverse filter
ds = filter([1 -1], 1, s);					% 1st difference
ds = hamming(ns) .* ds;						% window
R = flipud(fftfilt(conj(ds),flipud(ds)));	% autocorrelation vector
a = levinson(R,order);						% inverse filter coefficients

% apply it
fs = filter([1 -a], 1, s);					% inverse filter
fs = hamming(ns) .* fs;						% window
R = flipud(fftfilt(conj(fs),flipud(fs)));	% autocorrelation vector (applied to error)
R = R / R(1);								% normalize

% hunt voicing peak over range from 2.5 ms to half window size - 2.5 ms
ts = round(sr*.0025);						% 2.5 ms in samples
vp = find(diff([0 ; diff(R(ts+1:round(ns/2)-ts))] > 0) < 0) + ts;	% peak indices
v = R(vp);							% normalized values
k = find(v >= thresh);						% peaks exceeding threshold
if isempty(k),
	return;										% none
elseif k < 2,
	vp = vp(k);									% one	
	v = v(k);
else,								% heuristics to avoid pitch doubling/halving
	p = vp / vp;
	p = [0 , p(:,end)'];					% proportional peak periods
	px = linspace(0,1,length(p));			% ideal proportions
	if all(p > px-.02) & all(p < px+.02) & v(2) >= thresh,	% matches period repetition:  voiced
		if isF,
			vp = vp(1);							% female:  1st peak is probable pitch period
		else,
			vp = vp(2);							% male:  2nd peak is probable pitch period
		end;
	else,									% non-ideal pattern, result possibly bogus
		[v,vp] = max(R(ts+1:round(ns/2)-ts));	% use max peak
		vp = vp + ts;
	end;
end;

% convert pitch period to Hz
F0 = round(sr / (vp-1));


%=============================================================================
% CONFIGSPECTRA  - configure spectral analysis
%
%   returns [] on cancel

function config = ConfigSpectra(config);

width = 350;
height = 470;
pos = CenteredDialog(gcf, width, height);

cfg = dialog('Name', 'Configure Spectral Params', ...
	'Tag', 'MVIEW', ...
	'Position', pos, ...
	'menubar', 'none', ...
	'UserData', 0, ...
	'keyPressFcn', 'set(gcbf,''UserData'',1);uiresume');

set(cfg, 'units', 'characters');
figPos = get(cfg, 'position');
h = figPos(4);			% height in characters

% nudge step size
h = h - 3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Nudge stepsize (msecs):', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
nudgeH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.NUDGE), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% analysis window size
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Analysis window (msecs):', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
winH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.WSIZE), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% LPC order
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Number of LPC coeffs:', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
orderH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.ORDER), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% # FFTs
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','# FFT eval points:', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
fftH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.FRAME), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% averaging window
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Averaging window (msecs):', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
avgH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.AVGW), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% overlap
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Overlap (msecs):', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
olapH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.OLAP), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% spectral offset
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','SPL reference (dB):', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
soffH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.SOFF), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% spectral display cutoff
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Spectral Display Cutoff (Hz):', ...
	'Units', 'characters', ...
	'Position', [1 h 33 1.7]);
specLimH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %d',config.SPECLIM), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);

% preemphasis
h = h - 2.3;
p = [8 h+.7 11 1.5];
adaptH = uicontrol(cfg, ...
	'Style', 'checkbox', ...
	'HorizontalAlignment', 'left', ...
	'String', 'Adaptive', ...
	'Value', (config.PREEMP<0), ...
	'Units', 'characters', ...
	'Position', p);
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','pre-emphasis:', ...
	'Units', 'characters', ...
	'Position', [21 h 13 1.7]);
preempH = uicontrol(cfg, ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'String', sprintf(' %.2f',abs(config.PREEMP)), ...
	'Units', 'characters', ...
	'Position', [35 h+.3 10 2]);
	
% anal
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Active Analyses:', ...
	'Units', 'characters', ...
	'Position', [6 h-1 18 1.7]);
ah(1) = uicontrol(cfg, ...
	'Style', 'checkBox', ...
	'String', 'LPC', ...
	'Value', bitget(config.ANAL,1), ...
	'Units', 'characters', ...
	'Position', [25 h+.25 9 2]);
ah(2) = uicontrol(cfg, ...
	'Style', 'checkBox', ...
	'String', 'DFT', ...
	'Value', bitget(config.ANAL,2), ...
	'Units', 'characters', ...
	'Position', [35 h+.25 10 2]);
ah(3) = uicontrol(cfg, ...
	'Style', 'checkBox', ...
	'String', 'AVG', ...
	'Value', bitget(config.ANAL,3), ...
	'Units', 'characters', ...
	'Position', [25 h-1.55 9 2]);
ah(4) = uicontrol(cfg, ...
	'Style', 'checkBox', ...
	'String', 'CEPS', ...
	'Value', bitget(config.ANAL,4), ...
	'Units', 'characters', ...
	'Position', [35 h-1.55 10 2]);
	
% sex
h = h - 4;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Subject Gender:', ...
	'Units', 'characters', ...
	'Position', [6 h 18 1.7]);
p = [25 h+.2 20 2];
sexH = uicontrol(cfg, ...
	'Style', 'popupmenu', ...
	'HorizontalAlignment', 'left', ...
	'String', 'Male|Female', ...
	'value', config.ISF+1, ...
	'Units', 'characters', ...
	'Position', p);

% spectrogram
h = h - 2.3;
uicontrol(cfg, ...
	'Style','text', ...
	'HorizontalAlignment', 'right', ...
	'String','Spectrogram:', ...
	'Units', 'characters', ...
	'Position', [6 h 18 1.7]);
p = [25 h+.2 20 2];
spH = uicontrol(cfg, ...
	'Style', 'popupmenu', ...
	'HorizontalAlignment', 'left', ...
	'String', 'wideband|mid 1|mid 2|narrow', ...
	'value', config.MULT, ...
	'Units', 'characters', ...
	'Position', p);

% buttons
uicontrol(cfg, ...
	'Position',[width/2-70 15 60 30], ...
	'String','OK', ...
	'Callback','set(gcbf,''UserData'',1);uiresume');
uicontrol(cfg, ...
	'Position',[width/2+10 15 60 30], ...
	'String','Cancel', ...
	'Callback','uiresume');

% wait for input
uiwait(cfg);
if ~ishandle(cfg), config = []; return; end;
if get(cfg, 'UserData'),
	anal = get(ah, 'value');
	anal = anal{4}*8 + anal{3}*4 + anal{2}*2 + anal{1};
	soff = str2num(get(soffH, 'string'));
	if soff < 1, soff = 1; end;
	config = struct('NUDGE', str2num(get(nudgeH, 'string')), ...
					'WSIZE', str2num(get(winH, 'string')), ...
					'ORDER', str2num(get(orderH, 'string')), ...
					'FRAME', str2num(get(fftH, 'string')), ...
					'AVGW', str2num(get(avgH, 'string')), ...
					'OLAP', str2num(get(olapH, 'string')), ...
					'PREEMP', str2num(get(preempH, 'string')), ...
					'SOFF', soff, ...
					'SPECLIM', str2num(get(specLimH, 'string')), ...
					'ANAL', anal, ...
					'MULT', get(spH, 'value'), ...
					'ISF', get(sexH, 'value')-1 );
	if get(adaptH, 'value'), config.PREEMP = -config.PREEMP; end;
else,
	config = [];
end;
delete(cfg);


%=============================================================================
% GETLBLPAIR  - get offsets of label pair bracketing cursor
%
%	args:  state.LABELS, state.CURSOR
%
% returns h,t (msecs) of bracketing pair if any, else h = inf

function [h,t] = GetLblPair(labels, cursor)

h = inf; t = inf;
if isempty(labels), return; end;
labels = {labels.OFFSET};
if length(labels) < 2, return; end;
n = 1;
while n < length(labels),
	if cursor>=labels{n} & cursor<=labels{n+1}, break; end;
	n = n + 1;
end;
if n == length(labels), return; end;	% no bracketing pair
h = labels{n};
t = labels{n+1};


%=============================================================================
% GETNAME  - get export variable name

function name = GetName(name, ts)

width = 250;
height = 100;
pos = CenteredDialog(gcf, width, height);

cfg = dialog('Name', ts, ...
	'Tag', 'MVIEW', ...
	'menubar', 'none', ...
	'Position', pos, ...
	'KeyPressFcn', 'set(gcbf,''UserData'',1);uiresume', ...
	'UserData', 0);

% name field
eh = uicontrol(cfg, ...
	'Position', [20 60 width-40 25], ...
	'Style', 'edit', ...
	'HorizontalAlignment', 'left', ...
	'Callback', 'set(gcbf,''UserData'',1);uiresume', ...
	'String', name);

% OK, cancel buttons
uicontrol(cfg, ...		% buttons
	'Position',[width/2-70 15 60 25], ...
	'String','OK', ...
	'Callback','set(gcbf,''UserData'',1);uiresume');
uicontrol(cfg, ...
	'Position',[width/2+10 15 60 25], ...
	'String','Cancel', ...
	'Callback','uiresume');

% wait for input
uiwait(cfg);
if get(cfg, 'UserData'),
	name = get(eh, 'string');
else,
	name = [];
end;
delete(cfg);


%=============================================================================
% EDITLABEL  - edit label
%
%	returns [] on cancel, 0 if label is to be deleted

function label = EditLabel(label, id, useDel)

if nargin < 3, useDel = 0; end;

width = 280;
height = 140;
pos = CenteredDialog(gcf, width, height);

cfg = dialog('Name', [id ' Label'], ...
	'Tag', 'MVIEW', ...
	'menubar', 'none', ...
	'Position', pos, ...
	'UserData', 0, ...
	'keyPressFcn', 'set(gcbf,''UserData'',1);uiresume');

uicontrol(cfg, ...		% name
	'Position', [10 105 40 20], ...
	'HorizontalAlignment', 'right', ...
	'String','Name:', ...
	'Style','text');
name = uicontrol(cfg, ...
	'Position',[55 105 85 22], ...
	'Style','edit', ...
	'String', [' ',label.NAME], ...
	'HorizontalAlignment', 'left');
	
uicontrol(cfg, ...		% offset
	'Position', [145 105 50 20], ...
	'HorizontalAlignment', 'right', ...
	'String','Offset:', ...
	'Style','text');
offset = uicontrol(cfg, ...
	'Position',[200 105 60 22], ...
	'Style','edit', ...
	'String', sprintf(' %.1f',label.OFFSET), ...
	'HorizontalAlignment', 'left');

uicontrol(cfg, ...		% hook
	'Position', [10 70 70 20], ...
	'HorizontalAlignment', 'right', ...
	'String','Note:', ...
	'Style','text');
if ischar(label.HOOK) | isempty(label.HOOK), s = [' ',label.HOOK]; e = 'on'; else, s = ' <data>'; e = 'inactive'; end;
note = uicontrol(cfg, ...
	'Position',[85 70 175 22], ...
	'Style','edit', ...
	'Enable', e, ...
	'String', s, ...
	'HorizontalAlignment', 'left');


% buttons
if useDel,
	uicontrol(cfg, ...
		'Position',[width/2-100 15 60 30], ...
		'String','OK', ...
		'Callback','set(gcbf,''UserData'',1);uiresume');
	uicontrol(cfg, ...
		'Position',[width/2-30 15 60 30], ...
		'String','Cancel', ...
		'Callback','set(gcbf,''UserData'',0);uiresume');
	uicontrol(cfg, ...
		'Position',[width/2+40 15 60 30], ...
		'String','Delete', ...
		'Callback','set(gcbf,''UserData'',-1);uiresume');
else,
	uicontrol(cfg, ...
		'Position',[width/2-70 15 60 25], ...
		'String','OK', ...
		'Callback','set(gcbf,''UserData'',1);uiresume');
	uicontrol(cfg, ...
		'Position',[width/2+10 15 60 25], ...
		'String','Cancel', ...
		'Callback','set(gcbf,''UserData'',0);uiresume');
end;

% wait for input
uiwait(cfg);
switch get(cfg, 'userData'),
	case 1,		% OK
		label.NAME = strtok(get(name, 'String'));
		offset = str2num(get(offset, 'String'));
		if ~isempty(offset) & offset>0, label.OFFSET = offset; end;
		if ischar(label.HOOK) | isempty(label.HOOK), label.HOOK = get(note, 'String'); end;
	case 0,		% Cancel
		label = [];
	case -1,	% Delete
		label = -1;
end;
delete(cfg);


%=============================================================================
% FITCIRCLE  - fit a circle to 3 circumference points

function [c,r] = FitCircle(p)

ax = p(1,1); ay = p(1,2);
bx = p(2,1); by = p(2,2);
cx = p(3,1); cy = p(3,2);

D = 2 * (ay.*cx + by.*ax - by.*cx - ay.*bx - cy.*ax + cy.*bx);
if D == 0,
	r = 0;
	return;		% points are collinear
end;

cenX = (by.*ax.*ax - cy.*ax.*ax - by.*by.*ay + cy.*cy.*ay + bx.*bx.*cy + ay.*ay.*by + cx.*cx.*ay - cy.*cy.*by - cx.*cx.*by - bx.*bx.*ay + by.*by.*cy - ay.*ay.*cy) ./ D;
cenY = (ax.*ax.*cx + ay.*ay.*cx + bx.*bx.*ax - bx.*bx.*cx + by.*by.*ax - by.*by.*cx - ax.*ax.*bx - ay.*ay.*bx - cx.*cx.*ax + cx.*cx.*bx - cy.*cy.*ax + cy.*cy.*bx) ./ D;
c = [cenX,cenY];
r = sqrt((ax - cenX).^2 + (ay - cenY).^2);


%=============================================================================
% GETVAL  - get trajectory value at offset
%
%	MODE 0:  floor of time->sample conversion (computed directly in SetCursor)
%		 1:  nearest sample
%		 2:  linear interpolation
%		 3:  cubic interpolation (4 pt neighborhood)

function d = GetVal(offset, traj, sRate, mode)

% get bracketing samples
s = offset * sRate / 1000;			% fractional samples (0-based)
s1 = floor(s) + 1;
s2 = s1 + 1;
tMax = size(traj,1);

% handle end conditions
if mode > 2,
	s0 = s1 - 1;
	s3 = s1 + 2;
	if s0<1 | s3>tMax, mode = 2; end;
end;
if s1<1 | s2>tMax, mode = 1; end;

% interpolation method
switch mode,
	case 0,		% floor of time->sample conversion
		d = traj(s1,:);
	case 1,		% nearest neighbor
		s1 = round(s)+1;
		if s1 > tMax, s1 = tMax; end;
		d = traj(s1,:);
	case 2,		% linear interpolation
		v = traj(s1:s2,:);
		d = v(1,:) + diff(v) * (s + 1 - s1);
	case 3,		% cubic interpolation (4 pt neighborhood)
		d = interp1([s0:s3], traj(s0:s3,:), s, '*cubic');
end;


%=============================================================================
% GETVALS  - return displayed non-audio values at current cursor offset
%
% returns values and labels of displayed trajectory components

function [vals,labs] = GetVals(state)

labs = {};
vals = [];

% displayed mvt components
names = {state.DATA.NAME};
tempMap = state.TEMPMAP;
panels = state.TPANELS;
nComps = {state.DATA.NCOMPS};
xyz = 'xyz';
for mi = 1 : length(tempMap),
	if panels(mi).SR > 5000, continue; end;		% don't include audio
	[ti,mod,comp,ac] = ParseTempMap(names, tempMap{mi}, nComps);

% monodimensional
	if nComps{ti}==1,
		switch mod,
			case 1,		% unmodified
				s = state.DATA(ti).SIGNAL; 
			case 2,		% spectrogram (ignore)
				continue;
			otherwise,	% modified (get signal from display)
				s = get(panels(mi).LH,'ydata')';
		end;

% multidimensional
	else,
		if mod > 1,
			if ac,
				s = state.DATA(ti).SIGNAL(:,7+(mod-2)*4);
			else,
				s = state.DATA(ti).SIGNAL(:,find(comp)+(mod-1)*4-1);
			end;
		else,
			k = [1 : 3];
			if mod > 1, k = k + (mod-2)*4 - 1; end;
			s = state.DATA(ti).SIGNAL(:,k);
			if ~ac, s = s(:,find(comp)); end;
		end;
	end;
	sr = panels(mi).SR;
	sn = tempMap{mi};

% append values
	d = GetVal(state.CURSOR, s, sr, 1);
	if (nComps{ti}==1) | (mod>1 & ac),
		labs{end+1} = sn;
		vals(end+1) = d;
	else,
		comp = find(comp);
		nc = length(comp);
		for k = 1 : nc,
			if ac,
				labs{end+1} = [sn,xyz(k)];
			else,
				labs{end+1} = [sn(1:end-nc),sn(end-(nc-k))];
			end;
			vals(end+1) = d(k);
		end;
	end;
end;		


%=============================================================================
% INITCONTROLS  - set up display menus and controls

function [cfl,cf,hf,tf,xfl,xf,yfl,yf,zfl,zf,slider,autoMenu,lblMenu,fmtsMenu] = InitControls(fh, contrast, lblProc, auto, is3D, fmts)

% cursor field			
cfl = uicontrol(fh, ...								
	'style', 'text', ...
	'horizontalAlignment', 'right', ...
	'string', 'Cursor ', ...
	'units', 'characters', ...
	'backgroundColor', get(fh, 'color'), ...
	'foregroundColor', [1 1 1], ...
	'position', [1 5.0 9 1]);
cf = uicontrol(fh, ...
	'style', 'edit', ...
	'horizontalAlignment', 'left', ...
	'units', 'characters', ...
	'string', '0', ...
	'position', [11 4.8 12 1.8], ...
	'callback', 'mview CURCHG');

% head field	
uicontrol(fh, ...								
	'style', 'text', ...
	'horizontalAlignment', 'right', ...
	'string', 'Head ', ...
	'units', 'characters', ...
	'backgroundColor', get(fh, 'color'), ...
	'foregroundColor', [1 1 1], ...
	'position', [1 3.0 9 1]);
hf = uicontrol(fh, ...
	'style', 'edit', ...
	'horizontalAlignment', 'left', ...
	'units', 'characters', ...
	'string', '0', ...
	'position', [11 2.8 12 1.8], ...
	'callback', 'mview(''SELCHG'',1)');

% tail field
uicontrol(fh, ...								
	'style', 'text', ...
	'horizontalAlignment', 'right', ...
	'string', 'Tail ', ...
	'units', 'characters', ...
	'backgroundColor', get(fh, 'color'), ...
	'foregroundColor', [1 1 1], ...
	'position', [1 1.0 9 1]);
tf = uicontrol(fh, ...
	'style', 'edit', ...
	'horizontalAlignment', 'left', ...
	'units', 'characters', ...
	'string', '0', ...
	'position', [11 0.8 12 1.8], ...
	'callback', 'mview(''SELCHG'',2)');
	
% X field
xfl = uicontrol(fh, ...								
	'style', 'text', ...
	'horizontalAlignment', 'right', ...
	'string', 'X', ...
	'units', 'characters', ...
	'backgroundColor', get(fh, 'color'), ...
	'foregroundColor', [1 1 1], ...
	'position', [23 5.0 5 1]);
xf = uicontrol(fh, ...
	'style', 'edit', ...
	'horizontalAlignment', 'left', ...
	'units', 'characters', ...
	'string', '', ...
	'enable', 'inactive', ...
	'position', [29 4.8 12 1.8]);

% Y field	
yfl = uicontrol(fh, ...								
	'style', 'text', ...
	'horizontalAlignment', 'right', ...
	'string', 'Y', ...
	'units', 'characters', ...
	'backgroundColor', get(fh, 'color'), ...
	'foregroundColor', [1 1 1], ...
	'position', [23 3.0 5 1]);
yf = uicontrol(fh, ...
	'style', 'edit', ...
	'horizontalAlignment', 'left', ...
	'units', 'characters', ...
	'string', '', ...
	'enable', 'inactive', ...
	'position', [29 2.8 12 1.8]);

% Z field	
zfl = uicontrol(fh, ...								
	'style', 'text', ...
	'horizontalAlignment', 'right', ...
	'string', 'Z', ...
	'units', 'characters', ...
	'backgroundColor', get(fh, 'color'), ...
	'foregroundColor', [1 1 1], ...
	'position', [23 1.0 5 1]);
zf = uicontrol(fh, ...
	'style', 'edit', ...
	'horizontalAlignment', 'left', ...
	'units', 'characters', ...
	'string', '', ...
	'enable', 'inactive', ...
	'position', [29 0.8 12 1.8]);

% spectrogram slider
set(xf, 'units', 'pixels'); 
pos = get(xf, 'position');
dy = pos(2) + pos(4);
set(zf, 'units', 'pixels'); 
pos = get(zf, 'position');
pos = [pos(1)+pos(3)+10 , pos(2) , 10 , dy-pos(2)];
slider = uicontrol(fh, ...
	'style', 'slider', ...
	'min', 1, 'max', 30, ...
	'value', contrast, ...
	'units', 'pixels', ...
	'position', pos, ...
	'toolTipString', 'Adjust spectrogram contrast', ...
	'callback', 'mview CONTRAST');

% menus	

% MVIEW menu
menu = uimenu(fh, 'label', 'MVIEW');
uimenu(menu, 'label', 'About MVIEW...', ...
	'callback', 'mview ABOUT');
if auto, cs = 'on'; else, cs = 'off'; end;
autoMenu = uimenu(menu, 'label', 'Auto Update', ...
	'separator', 'on', ...
	'checked', cs, ...
	'callback', 'mview AUTO');
uimenu(menu, 'label', 'Update', ...
	'accelerator', 'U', ...
	'callback', 'mview UPDATE');
uimenu(menu, 'label', 'Set Head', ...
	'accelerator', 'D', ...
	'callback', 'mview(''SELCHG'',-1)');
uimenu(menu, 'label', 'Set Tail', ...
	'accelerator', 'T', ...
	'callback', 'mview(''SELCHG'',-2)');
h = uimenu(menu, 'label', 'Play');
ph(1) = uimenu(h, 'label', 'Selection', ...
	'accelerator', 'P', ...
	'callback', 'mview(''PLAY'',1)');
ph(2) = uimenu(h, 'label', 'Entire File', ...
	'callback', 'mview(''PLAY'',2)');
ph(3) = uimenu(h, 'label', 'To Cursor', ...
	'callback', 'mview(''PLAY'',3)');
ph(4) = uimenu(h, 'label', 'From Cursor', ...
	'callback', 'mview(''PLAY'',4)');
ph(5) = uimenu(h, 'label', '150ms @ Cursor', ...
	'callback', 'mview(''PLAY'',5)');
ph(6) = uimenu(h, 'label', 'Between Labels', ...
	'callback', 'mview(''PLAY'',6)');
ph(7) = uimenu(h, 'label', 'Alternate Track', ...
	'accelerator', '8', ...
	'separator', 'on', ...
	'callback', 'mview(''PLAY'',7)');
set(ph, 'userData', ph);
uimenu(menu, 'label', 'Report', ...
	'callback', 'mview REPORT');
if fmts, cs = 'on'; else, cs = 'off'; end;
fmtsMenu = uimenu(menu, 'label', 'Track Formants', ...
	'accelerator', 'J', ...
	'checked', cs, ...
	'callback', 'mview TRACKFMTS');
uimenu(menu, 'label', 'Shrink Selection', ...
	'separator', 'on', ...
	'callback', 'mview(''SELCHG'',-3)');
uimenu(menu, 'label', 'Expand Selection', ...
	'callback', 'mview(''SELCHG'',-4)');
uimenu(menu, 'label', 'Shift Selection Left', ...
	'accelerator', 'L', ...
	'callback', 'mview(''SELCHG'',-5)');
uimenu(menu, 'label', 'Shift Selection Right', ...
	'accelerator', 'R', ...
	'callback', 'mview(''SELCHG'',-6)');
uimenu(menu, 'label', 'Save Selection...', ...
	'separator', 'on', ...
	'accelerator', 'S', ...
	'callback', 'mview(''SAVESEL'',1)');
uimenu(menu, 'label', 'Save All But Selection...', ...
	'callback', 'mview(''SAVESEL'',2)');
uimenu(menu, 'label', 'Save Configuration...', ...
	'callback', 'mview SAVECFG');
h = uimenu(menu, 'label', 'Duplicate Window');
uimenu(h, 'label','Temporal Display', ...
	'callback', 'mview(''CLONE'',1)');
uimenu(h, 'label','Spatial Display', ...
	'callback', 'mview(''CLONE'',2)');
uimenu(h, 'label','Entire Window', ...
	'separator','on', ...
	'callback', 'mview(''CLONE'',3)');
uimenu(menu, 'label', 'Close Window', ...
	'separator', 'on', ...
	'accelerator', 'W', ...
	'callback', 'close');
uimenu(menu, 'label', 'Close All', ...
	'callback', 'mview ABORT');
        
% Configuration menu
menu = uimenu(fh, 'label', 'Configure');
uimenu(menu, 'label', 'Spectral Analysis...', ...
	'accelerator', 'A', ...
	'callback', 'mview CFGSPEC');
uimenu(menu, 'label', 'Temporal Layout...', ...
	'accelerator', 'C', ...
	'callback', 'mview(''CFGTEMP'',''INIT'')');
h = uimenu(menu, 'label', 'Spatial Options');
uimenu(h, 'label', 'Hide Spline', 'callback','mview(''CFGSPAT'',1);');
if is3D,
	uimenu(h, 'label', '2D View (1)', ...
			'separator', 'on', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',2)');
	uimenu(h, 'label', '2D View (2)', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',3)');
	uimenu(h, 'label', '2D View (3)', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',4)');
	uimenu(h, 'label', '3D View (1)', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',5)');
	uimenu(h, 'label', '3D View (2)', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',6)');
	uimenu(h, 'label', '3D View (3)', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',7)');
	uimenu(h, 'label', 'Specify View', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',''GET'')');
	uimenu(h, 'label', 'Free Rotate', ...
			'callback', 'mview(''SPATPLOT'',''VIEW'',''ROT'')');
else, 
	uimenu(h, 'label', 'Fit Circle', 'callback', 'mview(''CFGSPAT'',2);'); 
end;
uimenu(menu, 'label','Set Common Scaling...', ...
	'callback', 'mview SETSCALING');

% Movement menu
menu = uimenu(fh, 'label', 'Movement');
uimenu(menu, 'label', 'Step Forward', ...
	'accelerator', 'F', ...
	'callback', 'mview(''NUDGE'',1)');
uimenu(menu, 'label', 'Step Backward', ...
	'accelerator', 'B', ...
	'callback', 'mview(''NUDGE'',-1)');
uimenu(menu, 'label', 'Shift Forward', ...
	'callback', 'mview(''NUDGE'',2)');
uimenu(menu, 'label', 'Shift Backward', ...
	'callback', 'mview(''NUDGE'',-2)');
uimenu(menu, 'label', 'Reflective Cycling', ...
	'separator', 'on', ...
	'callback', 'mview(''CYCLE'',69)');
uimenu(menu, 'label', 'Cycle Forward', ...
	'callback', 'mview(''CYCLE'',1)');
uimenu(menu, 'label', 'Cycle Backward', ...
	'callback', 'mview(''CYCLE'',-1)');
uimenu(menu, 'label', 'Stop Cycling', ...
	'separator', 'on', ...
	'accelerator', 'X', ...
	'callback', 'mview(''CYCLE'',0)');

% Labels menu
menu = uimenu(fh, 'label', 'Labels');
uimenu(menu, 'label', 'Make Label...', ...
	'callback', 'mview LMAKE');
uimenu(menu, 'label', 'Edit Labels...', ...
	'callback', 'mview LEDIT');
uimenu(menu, 'label', 'Clear All Labels', ...
	'accelerator', 'Y', ...
	'callback', 'mview LCLEAR');
uimenu(menu, 'label', 'Export Labels...', ...
	'separator', 'on', ...
	'accelerator', '9', ...
	'callback', 'mview LEXPORT');
uimenu(menu, 'label', 'Import Labels...', ...
	'callback', 'mview LIMPORT');
uimenu(menu, 'label', 'Save Labels...', ...
	'separator', 'on', ...
	'callback', 'mview LSAVE');
uimenu(menu, 'label', 'Load Labels...', ...
	'callback', 'mview LLOAD');
uimenu(menu, 'label', 'Set Sel to Lbl Pair', ...
	'callback', 'mview LSETSEL');
h = uimenu(menu, 'label', 'Labelling Behavior', ...
	'separator', 'on');
if isempty(lblProc), s = '<Default>'; else, s = lblProc; end;
lblMenu = uimenu(h, 'label', s);
uimenu(h, 'label', 'Clear', ...
	'separator', 'on', ...
	'callback', 'mview(''LSETPROC'',0);');
uimenu(h, 'Label', 'Select...', ...
	'callback', 'mview(''LSETPROC'',1);');
uimenu(h, 'Label', 'Configure...', ...
	'accelerator', 'K', ...
	'callback', 'mview(''LSETPROC'',2);');



%=============================================================================
% INITSPAT  - initialize spatial plot
%
%	usage:  h = InitSpat(ah, spatColors, range)
%
% where
%	AH is the spatial axis handle
%	SPATCOLORS are the plotting colors
%	RANGE holds the plotting bounds [xMin,yMin ; xMax,yMax]
%
% plots line objects (off axis)
%
% returns vector of plotted line handles H

function [h,c] = InitSpat(ah, spatColors, range)

delete(findobj(ah, 'type', 'line'));		% kill any existing objects

h = [];
if isempty(spatColors),						% if nothing to plot							
	set(ah, 'xtick',[], 'ytick',[], 'plotBoxAspectRatioMode','auto','dataAspectRatioMode','auto');
	axis normal;
	return;
end;

set(ah, 'xlim', range(:,1), 'ylim', range(:,2), ...
	'xticklabelmode','auto','xticklabelmode','auto'); %,'dataAspectRatio',[1 1 1]);
x = range(1,1) - 10;
y = range(2,1) - 10;						% create points out of axis
for ci = 1 : length(spatColors),
	line(x, y, 'color', spatColors(ci,:));
end;


%=============================================================================
% INITTRAJ  - initialize temporal trajectory plot
%
%	usage:  [th,ki] = InitTraj(data, dur, panDims, spreads, tempMap)
%
% where
%	DATA is the concurrently acquired dataset
%	DUR give duration in msecs
%	PANDIMS are the normalized bounds of the trajectory panels
%	SPREADS specifies common vertical scaling for movement
%	HT gives the current head:tail (msecs)
%	TEMPMAP gives the (topdown) panel order of trajectories to be plotted
%
% creates panel axes (spectrogram is double-height), plots full-range data
%
% returns an array of structs TH, one per created panel, with fields
%	AXIS  - panel axis handle
%	LH	  - created line handles
%	SR	  - sampling rate (Hz)
% 
% also returns KI, index into TH of spectrogram panel(s) (if any)

function [th,ki] = InitTraj(data, dur, panDims, spreads, tempMap)

names = {data.NAME};
for mi = 1 : length(tempMap),
	[ti, mod, comp] = ParseTempMap(names, tempMap{mi}, {data.NCOMPS});
	if ~ti, th = 0; ki = tempMap{mi}; return; end
	trajMap(mi) = ti;			% index into data
	modMap(mi) = mod;			% associated modification
	compMap{mi} = comp;			% displayed components
	if ti & data(ti).NCOMPS==1 & mod==2, 
		trajMap(mi) = -ti;		% spectrogram flagged with negated index
	end;
end;
k = find(trajMap == 0);			% delete unmatched names
if ~isempty(k),
	tempMap(k) = [];
	trajMap(k) = [];
	modMap(k) = [];
	compMap(k) = [];
end;

nPanels = length(trajMap) + sum(trajMap<0);	% spectrogram is double-height
th(nPanels - sum(trajMap<0)) = struct('AXIS',[], 'LH',[], 'SR',[]);
ki = [];
pos = panDims;
dh = pos(4) / nPanels;
pos(4) = dh;
ismac = strcmp(computer, 'MAC2'); 
if ismac,
	pos(4) = pos(4) + .002;
	k = .4; 						% trajectory component dimming factor
else, 
	k = .6; 
end;	

mi = length(modMap);			% panel index
for ti = fliplr(trajMap),		% plot bottom-up
	if ti > 0,					% all but spectrogram	
		sr = data(ti).SRATE;
		ts = floor(dur*sr/1000)+1;
		if data(ti).NCOMPS > 1,			% movement
			cc = data(ti).COLOR;
			for ci = 2 : data(ti).NCOMPS,
				cc = [cc ; cc(ci-1,:)*k];
			end;
			ah = axes('position', pos, 'colororder', cc, 'nextplot','add');
			switch modMap(mi),
				case 1,		% movement
					ci = find(compMap{mi});
				case 2,		% velocity
					if sum(compMap{mi}) == data(ti).NCOMPS,
						ci = 7;			% velocity magnitude
					else,
						ci = find(compMap{mi}) + 3;
					end;
				case 3,		% acceleration
					if sum(compMap{mi}) == data(ti).NCOMPS,
						ci = 11;		% acceleration magnitude
					else,
						ci = find(compMap{mi}) + 7;
					end;
			end;
			yMins = (max(data(ti).SIGNAL(1:ts,ci)) + min(data(ti).SIGNAL(1:ts,ci))) / 2;
			lh = plot(data(ti).SIGNAL(1:ts,ci) - repmat(yMins,ts,1));
			ylim = [-spreads(modMap(mi)) spreads(modMap(mi))]/2;
			if length(ci)==1 & any(ci == [4:6 8:10]),	% plot zero line (vel, acc except magnitude)
				line([1 ts], -[1 1].*yMins, 'color', 'w', 'lineStyle', ':');
			end;
		else,							% monodimensional
			ah = axes('position', pos);
			ylim = [0 1];
			cc = [1 1 1];
			switch modMap(mi),
				case 1,		% signal
					lh = plot(data(ti).SIGNAL(1:ts), 'color', data(ti).COLOR);
					ylim = data(ti).SPREAD;
				case 2,	;	% spectrogram
				case 3, 	% F0
					try,
						s = data(ti).SIGNAL(1:ts);
						sr = data(ti).SRATE;
						f0 = ComputeF0({s,sr},[],[80 600],sr);
						lh = plot(f0, 'color', data(ti).COLOR);
						ylim = [0 max([300,nanmax(f0)+30])];
						sr = length(f0)*sr/ts;
						ts = length(f0);
					catch,
						fprintf('error attempting F0 estimation\n');
						lh = plot(data(ti).SIGNAL(1:ts), 'color', data(ti).COLOR);
						ylim = data(ti).SPREAD;
					end;
				case 4, 	% RMS
					window = round(20*sr/1000);		% 20 msec filter window
					b = rectwin(window)./window;
					rms = sqrt(abs(filtfilt(b,1,data(ti).SIGNAL(1:ts).^2)));
					lh = plot(rms, 'color', data(ti).COLOR);
					ylim = [min(rms) max(rms)];
					ylim = ylim + [-.1 .1]*diff(ylim);
				case 5, 	% ZC
					wl = round(20*sr/1000);		% 20 msec filter window
					wl2 = ceil(wl/2);
					s = [zeros(wl2,1);data(ti).SIGNAL(1:ts);zeros(wl2,1)];
					zc = filter(rectwin(wl),1,[0;abs(diff(s>=0))]);
					zc = zc(wl2*2+1:end);
					lh = plot(zc, 'color', data(ti).COLOR);
					ylim = [min(zc) max(zc)];
					ylim = ylim + [-.1 .1]*diff(ylim);
				case {6,7}		% velocity (cm/sec)
					ds = data(ti).SIGNAL(1:ts);
					ds = data(ti).SRATE * [diff(ds([1 3])) ; (ds(3:end) - ds(1:end-2)) ; diff(ds([end-2 end]))] ./ 20;
					if modMap(mi) == 7, ds = abs(ds); end;
					lh = plot(ds, 'color', data(ti).COLOR);
					ylim = [min(ds) max(ds)];
					ylim = ylim + [-.1 .1]*diff(ylim);
					line([1 ts],[0 0],'color','w','linestyle',':');
			end;
		end;
		if ~diff(ylim), ylim = [0 1]; end;
		set(ah, 'xlim', [1 ts], 'ylim',ylim, 'xtick',[], 'ytick', [], 'box','on','hitTest','off');
		h = text(.01,.95, tempMap{mi}, ...
			'VerticalAlignment', 'top', ...
			'units', 'normal', ...
			'interpreter', 'none', ...
			'Color', cc(1,:));
		if ismac, set(h, 'fontname','geneva','fontsize',9); end;
	else,					% spectrogram
		spos = pos;
		spos(4) = spos(4) + dh;
		ah = axes('position', spos, 'xtick', [], 'ytick',[], 'box','on','hitTest','off');
		ki = [ki , mi];			% index of spectrogram panel in TH
		lh = [];
		sr = [];
		pos(2) = pos(2) + dh;
	end;
	th(mi).AXIS = ah;
	th(mi).LH = lh;
	th(mi).SR = sr;
	mi = mi - 1;
	pos(2) = pos(2) + dh;
end;


%=============================================================================
% MAKELIST of current labels

function labels = MakeList(state)

labels = {};
for i = 1 : length(state.LABELS),
	label = state.LABELS(i);
	if ischar(label.HOOK) | isempty(label.HOOK), sn = label.HOOK; else, sn = '(data)'; end;
	labName = label.NAME;
	if isempty(labName), labName = ' '; end;
	s = sprintf('%-12s %9.1f  %s', ...
		labName, ...
		label.OFFSET, ...
		sn);
	labels(end+1) = {s};
end;
		

%=============================================================================
% MOTIONLOOP  - step position while motion active

function MotionLoop(state)

if state.MOTION == 69,				% reflective
	toggle = 1;
	state.MOTION = 1;
	set(gcbf, 'userData', state);
else,
	toggle = 0;
end;
dir = state.MOTION;

while dir,
	state = get(gcbf, 'userData');		% refresh state to detect interrupt
	dir = state.MOTION;
	c = state.CURSOR + state.NUDGE*dir;
	if c < state.HEAD,				% wrap around
		if toggle, 
			state.MOTION = -state.MOTION; 
			c = state.HEAD;
		else,
			c = state.TAIL;
		end;
	elseif c > state.TAIL,
		if toggle, 
			state.MOTION = -state.MOTION; 
			c = state.TAIL;
		else,
			c = state.HEAD;
		end;
	end;
	state.CURSOR = c;
	set(gcbf, 'userData', state);
	SetCursor(state);
	drawnow;
end;


%=============================================================================
% PARSETEMPMAP  - parse displayed TEMPMAP entry
%
%	usage:  [ti, mod, comp] = ParseTempMap(loadedString, sel, comps)
%
% LOADEDSTRING is the cellstr list of trajectory names (TEMPMAP)
% SEL is the (possibly modified) trajectory to identify within these
% COMPS (matching LOADEDSTRING order) gives the number of available components for each trajectory
% if COMPS is empty it defaults to 3
%
% returns trajectory index TI (into DATA), MODification code, active COMPonents

function [ti, mod, comp, allComps] = ParseTempMap(loadedString, sel, comps)

mods = {'SPECT','F0','RMS','ZC','VEL','ABSVEL'};		% supported monodimensional data modifications
allComps = 0;											% true if all components selected

if all(sel > 'Z'), sel = upper(sel); end;

% find prefix movement selector (movement '', velocity 'v', acceleration 'a')
if sel(1) > 'Z',
	if sel(1)=='v', mod = 2; else, mod = 3; end;
	sel = sel(2:end);
else,
	mod = 1;
end;

% find suffix component selector
k = findstr(sel,'_');
if isempty(k),			% movement
	k = find(sel>'Z');
	if isempty(k),
		comp = [];				% all
		allComps = 1;
	else,
		comp = sel(k:end);		% xyz
		sel = sel(1:k-1);
	end;
else,					% mono-dimensional mods
	comp = sel(k+1:end);		% SPECT, F0, RMS, ZC, VEL, ABSVEL
	if isempty(strmatch(comp, mods, 'exact')),
		comp = [];				% traj name with form FOO_BAH
	else,
		sel = sel(1:k-1);
	end;
end;

% find trajectory index
ti = strmatch(upper(sel), loadedString, 'exact');
if isempty(ti),
	ti = 0;						% not found
	return;
end;

% multi-component trajectories
if isempty(comps) || comps{ti} > 1,
	if isempty(comp),	% unspecified (all)
		if isempty(comps),
			comp = [1 1 1];
		else,
			comp = [1 1 comps{ti}>2];
		end;
	else,				% specified
		comp = [any(comp=='x') , any(comp=='y') , any(comp=='z')];
	end;

% monodimensional data
else,
	if isempty(comp),
		mod = 1;		% data
	else,
		mod = strmatch(comp, mods, 'exact') + 1;
	end;
	comp = [];
end;


%=============================================================================
% PLOTSPECTRA  - plot spectral cross-section
%
% uses external function SPECTRA

function PlotSpectra(state)

mu = state.PREEMP;
if mu < 0, mu = []; end;
analI = find([bitget(state.ANAL,1) bitget(state.ANAL,2) bitget(state.ANAL,3) bitget(state.ANAL,4)]);
analS = {'LPC','DFT','AVG','CEPS'};
sex = 'MF';

fh = colordef('new', 'black');
a1 = subplot(3,1,1);			% speech axis
pos1 = get(a1, 'position');
a2 = subplot(3,1,3);			% spectrum axis
pos2 = get(a2, 'position');
pos2(4) = pos1(2) - pos2(2) - .1;
set(a2, 'position', pos2);

[h,s,mu,F0] = spectra(state.DATA(state.FI).SIGNAL, state.SRATE, state.CURSOR, ...
		'WSIZE',state.WSIZE, 'ANAL',analS(analI), ...
		'DEST', a2, 'PREEMP',mu, 'SEX',sex(state.ISF+1), 'SOFF', state.SOFF, ...
		'AVGW',state.AVGW, 'OVERLAP',state.OLAP, 'ORDER',state.ORDER);
legend(h, char(analS(analI)));

axes(a1);
ht = state.CURSOR + [-state.WSIZE state.WSIZE];
dx = 0;
if ht(1)<0, dx = ht(1); ht(1)=0; end;
if ht(2)>state.DUR, ht(2)=state.DUR; end;
hts = floor(ht*state.SRATE/1000) + 1;
s = state.DATA(state.FI).SIGNAL(hts(1):hts(2));
plot(s, 'w');
xlim = [1 length(s)];
ylim = get(state.FPANEL, 'ylim');
hts = floor((state.WSIZE + dx + state.WSIZE*[-.5 .5])*state.SRATE/1000) + 1;
if hts(1)<1, hts(1) = 1; end;
if hts(2)>length(s), hts(2) = length(s); end;
w = zeros(size(s));
w(hts(1):hts(2)) = hanning(diff(hts)+1) * (ylim(2)*.9);
line([1:length(w)],w,'color','g');

set(a1, 'xlim', xlim, 'ylim', ylim, ...
		'xtick', [], 'ytick', []);
line(xlim, [0 0], 'color', [.5 .5 .5], 'linestyle', ':');
title(sprintf('CURSOR = %.1f    WSIZE = %d    FRAME = %d    MU = %.2f', ...
		state.CURSOR, state.WSIZE, state.FRAME, mu));

a3 = axes('position', pos1, 'xlim', ht, 'ytick',[], 'color','none');
line([state.CURSOR, state.CURSOR], get(a3,'ylim'), 'color','c', 'linestyle', '--');
xlabel('msecs');

uicontrol(fh, ...					% cursor button
			'style', 'pushbutton', ...
			'units', 'characters', ...
			'string', 'Cursor', ...
			'position', [3 0 10 1.5], ...
			'callback', 'disp(''units: Hz, dB'');round(ginput)');
if F0 > 0,							% F0
	uicontrol(fh, ...
			'style', 'text', ...
			'units', 'characters', ...
			'string', sprintf('F0 = %d Hz', F0), ...
			'backgroundColor', get(fh, 'color'), ...
			'foregroundColor', [1 1 1], ...
			'position', [13 0 25 1.2]);
end;
set(fh, 'name', sprintf('%s @ %.1f', state.NAME, state.CURSOR), 'visible', 'on');


%=============================================================================
% PREEMP pre-emphasis

function s = preemp(s, mu)

if mu == 0, return; end;

if mu < 0,		% adaptive
	r0 = s * s';
	r1 = s * [0 s(1:end-1)]';
	mu = r1 ./ r0;
end;

s = filter([1 -mu], 1, s);


%=============================================================================
% SETBOUNDS  - update selection bounds
%
%	usage:  SetBounds(state, flag)
%
% FLAG = 0:  force update
% FLAG = 1:  update of selection bounds only
% FLAG = 2:  first time initialization

function SetBounds(state, flag)

if nargin<2, flag = ~state.AUTO; end;

% clip head/tail to slowest displayed channel
th = state.TPANELS;
minRate = inf;
for ti = 1 : length(th),
	if th(ti).SR < minRate, minRate = th(ti).SR; end;
end;
ht = 1000*floor([state.HEAD,state.TAIL]*minRate/1000)/minRate;
state.HEAD = ht(1);
state.TAIL = ht(2);

% update text fields
set(state.HEADF, 'string', sprintf(' %.1f',state.HEAD));
set(state.TAILF, 'string', sprintf(' %.1f',state.TAIL));

% update selection patch
hs = floor(state.HEAD*state.SRATE/1000)+1;	% msecs -> samps
ts = floor(state.TAIL*state.SRATE/1000)+1;
set(state.BOUNDS, 'xdata', [hs hs ts ts]);
if flag == 1, return; end;

% update temporal panels
set(state.SPATIALH,'visible','off');
set([state.CURSORL;findobj(state.CURSORH, 'tag', 'LABEL')], 'visible', 'off');
for ti = 1 : length(th),
	if isempty(th(ti).LH),			% flags spectrogram panel
		ka = th(ti).AXIS;
		delete(get(ka, 'children'));

% compute & display spectrogram (from frame index)
		if ts-hs < 200000,			% if not too big
			sd = diff(state.DATA(state.FI).SIGNAL(hs:ts));	% 1st diff pre-emphasis
			ns = length(sd);
			sr = state.SRATE;
			frame = min(ns,state.FRAME);
			wSize = state.MULT * floor(state.AVGW*sr/1000);	% window
			wSize = wSize + mod(wSize,2);		% ensure even
			shift = state.OLAP*sr/1000;			% overlap (fractional samples)
			nf = round(ns/shift);				% # frames
			w = hanning(wSize);
			b = zeros(frame, nf);
			sx = wSize/2 + 1;
			sd = [zeros(wSize/2,1) ; sd ; zeros(wSize,1)];
			for fi = 1 : nf,
				si = round(sx);
				pf = abs(fft(w .* sd(si:si+wSize-1),frame*2));
				b(:,fi) = pf(2:frame+1);		% drop DC, upper reflection
				sx = sx + shift;
			end;
			b = filter(ones(3,1)/3, 1, abs(b), [], 2);	% clean holes
			f = linspace(0,sr/2,frame);
			if state.SPECLIM < sr/2,
				f(find(f > state.SPECLIM)) = [];
				b = b(1:length(f),:);
			end;
			axes(ka);
			set(ka, 'xlim', [1 ns], 'ylim', [0 state.SPECLIM]);
			imagesc(1:ns, f, b);
			set(ka, 'ydir', 'normal', 'xtick', [], 'ytick', [], 'box', 'on');
			colormap(flipud(gray(state.NGRAYS).^get(state.CONTRAST,'value')));
			if state.FMTS,
				try,
					if isempty(state.PREEMP), pe = .98; else, pe = state.PREEMP; end;
 					s = state.DATA(state.FI).SIGNAL(hs:ts);
					if state.SRATE ~= 10000,
						[p,q] = rat(10000/state.SRATE);
						s = resample(s,p,q);
					end;
 					fmts = snackfmts(s,10000,'preemp',pe,'lpcord',14,'nform',5);
				catch,
					fprintf('error computing formants\n');
					fmts = [];
				end;
				if ~isempty(fmts),
					x = linspace(1,ns,size(fmts,1))';
					set(gca,'colororder',[0 0 1;0 1 0;1 0 0;0 .8 .8;.8 .8 0;.8 0 .8;.75 .75 .75]);
					line(x,fmts,'marker','.','markerSize',1,'linestyle','none');
				end;
			end;
		else,
			h = text(.01,.95, 'SPECTROGRAM (selection too large; suppressed)', ...
				'VerticalAlignment', 'top', ...
				'units', 'normal', ...
				'Color', 'w', ...
				'parent', ka);
		end;

% adjust trajectory display limits
	else,
		xlim = floor([state.HEAD state.TAIL]*th(ti).SR/1000)+1;	% msecs -> samps
		set(th(ti).AXIS, 'xlim', xlim);
	end;
end;

axes(state.CURSORH);
set(state.CURSORH, 'xlim', [state.HEAD state.TAIL]);
if flag ~= 2,
	if flag == 3,
		sh = state.SPATIALH;
		si = 1;
		for ti = state.SPATCHAN,
			set(sh(si), 'color', state.DATA(ti).COLOR);
			si = si + 1;
		end;
	end;
	drawnow; 
end;
set(state.SPATIALH,'visible','on');
set([state.CURSORL;findobj(state.CURSORH, 'tag', 'LABEL')], 'visible', 'on');

% update plotting procs
if ~isempty(state.PPSTATE),
	pproc = state.PPROC;
	if ischar(pproc), 
		pproc = {pproc}; 
	elseif ischar(pproc{1}),
		pproc = {pproc};
	end;
	for k = 1 : length(pproc),
		pName = pproc{k};
		if iscell(pName), pName = pName{1}; end;
		feval(pName,state.PPSTATE{k},'UDBNDS',state.HEAD,state.TAIL);
	end;
end;


%=============================================================================
% SETCURSOR  - update cursor location
%
%	usage:  SetCursor(state, resetZoom)
%
% if RESETZOOM is nonzero only zoomed waveform display is updated

function SetCursor(state, resetZoom)

if nargin < 2, resetZoom = 0; end;

% update zoomed waveform
sr = state.SRATE;
c = floor(state.CURSOR*sr/1000)+1;				% cursor msecs->samples
signal = state.DATA(state.FI).SIGNAL;
if size(signal,2) > 1, signal = signal(:,1); end;

ns = round(state.ZOOMW/1000*sr);
h = c - round(ns/2);
t = h + ns - 1;
if h < 1,
	s = [zeros(-h+1,1) ; signal(1:t)];
elseif t > length(signal),
	s = [signal(h:end) ; zeros(t-length(signal),1)];
else,
	s = signal(h:t);
end;
set(state.ZOOM, 'xData', [1:ns], 'yData', s);
if resetZoom, return; end;

set(state.CURSORL, 'xData', [state.CURSOR state.CURSOR]);
set(state.CURSORF, 'string', sprintf(' %.1f',state.CURSOR));

% compute & plot spectra
if bitand(state.ANAL,3),
	ns = round(state.WSIZE/1000*sr);			% analysis window (msecs->samples)
	frame = state.FRAME;
	h = c - round(ns/2);
	if h < 1, h = 1; end;
	t = h + ns - 1;
	if t > length(signal),
		t = length(signal);
		h = t - ns + 1;
	end;
	signal = signal(h:t);
	signal = hanning(ns).*preemp(signal, state.PREEMP);
	f = linspace(0, sr/2, frame+1);
	f(1) = [];
	ylim = get(state.SPECTRA, 'ylim');
	ylimChg = 0;
	if bitand(state.ANAL,1),	% LPC
%		[a,g] = lpcg(signal, state.ORDER);
		R = flipud(fftfilt(conj(signal),flipud(signal)));	% unbiased autocorrelation estimate
		a = levinson(R, state.ORDER);						% LPC
		g = sqrt(real(sum((a').*R(1:state.ORDER+1,:))));	% gain
		p = freqz(g, a, frame, sr);
		p = 20*log10(abs(p/state.SOFF+eps)');
		if min(p)<ylim(1), ylim(1) = min(p)-10; ylimChg = 1; end;
		if max(p)>ylim(2), ylim(2) = max(p)+10; ylimChg = 1; end;
		set(state.SPECTRAL(1), 'xData', f, 'yData', p);		% LPC line
	elseif length(get(state.SPECTRAL(1), 'xData')) > 1,
		set(state.SPECTRAL(1), 'xData', 0, 'yData', 0);
	end;
	if bitand(state.ANAL,2),	% DFT
		p = abs(fft(signal', frame*2));						% magnitude spectrum
		p = p(2:frame+1);									% drop DC, upper reflection
		p = 20*log10(p/state.SOFF+eps);
		if min(p)<ylim(1), ylim(1) = min(p)-10; ylimChg = 1; end;
		if max(p)>ylim(2), ylim(2) = max(p)+10; ylimChg = 1; end;
		set(state.SPECTRAL(2), 'xData', f, 'yData', p);		% DFT
	elseif length(get(state.SPECTRAL(2), 'xData')) > 1,
		set(state.SPECTRAL(2), 'xData', 0, 'yData', 0);
	end;
	if ylimChg,
		set(state.SPECTRA, 'ylim', ylim);
	end;
else,
	set(state.SPECTRAL, 'xData', 0, 'yData', 0);		% clear display
end;

% update value @ cursor readout
t = state.CURSOR;
mode = state.INTERPMODE;
if ~isempty(state.CLICKINFO),
	ti = state.CLICKINFO(1);
	d = GetVal(t, state.DATA(ti).SIGNAL, state.DATA(ti).SRATE, mode);
	if length(state.CLICKINFO) < 4,		% monodimensional
		if state.CLICKINFO(3) == 2,		% mod==2 (spectrogram)
			set(state.XFL, 'string', 'Hz');
			xy = get(state.TPANELS(state.SPECGRAM).AXIS, 'currentPoint');
			y = round(xy(1,2));
			ylim = get(state.TPANELS(state.SPECGRAM).AXIS, 'ylim');
			if y > ylim(1) & y < ylim(2),
				set(state.XF, 'string', sprintf(' %.0f',xy(1,2)));
			end;
		else,				% monodimensional
			if state.CLICKINFO(3) > 2,		% get derived signal from plotted values
				ah = state.TPANELS(state.CLICKINFO(2)).AXIS;
				lh = findobj(ah, 'type', 'line', 'linestyle','-');
				s = get(lh,'ydata')';
				d = GetVal(t,s,state.DATA(ti).SRATE, mode);
			end;
			set(state.XF, 'string', sprintf(' %.1f',d));
		end;
	else,
		comp = state.CLICKINFO(4:end);
		switch 	state.CLICKINFO(3),		% modifier
			case 1, 
				ci = comp .* [1:3];
			case 2,
				if sum(comp) == state.DATA(ti).NCOMPS,
					ci = [7 0 0];		% velocity magnitude
					comp = [1 0 0];
				else,
					ci = comp .* [4:6];
				end;
			case 3,
				if sum(comp) == state.DATA(ti).NCOMPS,
					ci = [11 0 0];		% acceleration magnitude
					comp = [1 0 0];
				else,
					ci = comp .* [8:10];
				end;
		end;
		if comp(1), set(state.XF, 'string', sprintf(' %.1f', d(ci(1)))); end;
		if comp(2), set(state.YF, 'string', sprintf(' %.1f', d(ci(2)))); end;
		if comp(3), set(state.ZF, 'string', sprintf(' %.1f', d(ci(3)))); end;
	end;
end;

% update spatial positions
sh = state.SPATIALH;
si = 1;
spi = state.SPLINE;
p = [];
for ti = state.SPATCHAN,
	if mode,
		d = GetVal(t, state.DATA(ti).SIGNAL, state.DATA(ti).SRATE, mode);
	else,		% compute floor of msec->samp conversion directly
		d = state.DATA(ti).SIGNAL(floor(t*state.DATA(ti).SRATE/1000)+1,:);
	end;
	if state.IS3D,
		set(sh(si), 'xData', d(1), 'yData', d(2), 'zData', d(3));
	else,
		set(sh(si), 'xData', d(1), 'yData', d(2));
	end;
	si = si + 1;
	if ~isempty(spi),
		spix = find(ti == abs(spi));
		if ~isempty(spix),
			if state.IS3D,
				p(spix,:) = d(1:3);
			else,
				p(spix,:) = d(1:2);
			end;
		end;
	end;
end;

% update plotting procs
if ~isempty(state.PPSTATE),
	pproc = state.PPROC;
	if ischar(pproc), 
		pproc = {pproc}; 
	elseif ischar(pproc{1}),
		pproc = {pproc};
	end;
	for k = 1 : length(pproc),
		pName = pproc{k};
		if iscell(pName), pName = pName{1}; end;
		feval(pName,state.PPSTATE{k},'UDCURS',state.CURSOR);
	end;
end;

% update contour
% delay holds offset of 1st US frame w.r.t. EMA in secs 
%  >0: US starts after EMA; <0 US starts before EMA
if ~isempty(state.CONTOURS),
	c = state.CONTOURS;
	nc = size(c,3);
	fps = state.DATA(1).SOURCE.FPS;
	delay = state.DATA(1).SOURCE.DELAY * 1000;
	xs = (t-delay)*fps/1000 + 1;
	hs = floor(xs); 
	ts = ceil(xs); 
	if hs < 1 || ts > nc,
		set(state.SPLINEL,'xData',NaN,'yData',NaN,'zData',NaN);
	else,
		c = [interp1([hs,ts],squeeze(c(:,1,hs:ts))',xs,'linear');interp1([hs,ts],squeeze(c(:,2,hs:ts))',xs,'linear');interp1([hs,ts],squeeze(c(:,3,hs:ts))',xs,'linear')]';
		k = [0 ; cumsum(sqrt(sum(diff(c).^2,2)))];
		c = interp1(k,c,linspace(0,k(end),100),'spline');
		set(state.SPLINEL,'xData',c(:,1),'yData',c(:,2),'zData',c(:,3));
	end;

% update splines
elseif ~isempty(p),
	k = find(any(isnan(p),2));
	p(k,:) = [];
	if size(p,2) > 2,
		if state.IS3D,
			set(state.SPLINEL, 'xData', p(:,1), 'yData', p(:,2), 'zData', p(:,3));
			return;
		elseif spi(1)<0,
			ip = p;
		else,
			[v,k] = sort(p(:,1));
			p = p(k,:);
			xx = linspace(p(1,1),p(end,1),21)';	% compute & plot 2D spline
			yy = interp1(p(:,1),p(:,2),xx,'spline');
			ip = [xx,yy];
		end;
	elseif isempty(p),
		ip = get(state.SPATIALA, 'xlim');
		ip(1) = ip(1) - 10;
	elseif spi(1)<0,
		ip = p;						% plot line
	else,
		[v,k] = sort(p(:,1));
		p = p(k,:);
		xx = linspace(p(1,1),p(end,1),21)';	% compute & plot 2D spline
		yy = interp1(p(:,1),p(:,2),xx,'spline');
		ip = [xx,yy];
	end;
	set(state.SPLINEL, 'xData', ip(:,1), 'yData', ip(:,2));

% fitted circle (2D, visible only)
	if size(p,1)>=3 & strcmp(get(state.CIRCLEL,'visible'),'on'),
		[c,r] = FitCircle(p);
		if r > 0,
			if r < 50,
				th = 0:pi/50:2*pi;
				x = r*cos(th) + c(1);
				y = r*sin(th) + c(2);
			else,
				x = p(1,1); y = p(1,2);
			end;
			set(state.CIRCLEL,'xdata',x, 'ydata',y);
		end;
	end;
	
end;


%=============================================================================
% TEMPCFG  - configure temporal layout
%
%	usage:  tempMap = TempCfg(loadedNames, displayedNames, comps, colors)
%

function tempMap = TempCfg(loadedNames, displayedNames, comps, colors, fh)

width = 290;
height = 330;
pos = CenteredDialog(gcf,width,height);
cfg = dialog('Name', 'Configure Temporal Layout', ...
	'Tag', 'MVIEW', ...
	'Position', pos, ...
	'menubar', 'none', ...
	'windowStyle', 'normal', ...
	'keyPressFcn', 'set(gcbf,''UserData'',1);uiresume');

% loaded trajectories
h = height - 30;
uicontrol(cfg, ...			
	'Style', 'text', ...
	'HorizontalAlignment','left', ...
	'String', 'Loaded', ...
	'Position', [30 h 70 17]);
loaded = uicontrol(cfg, ...
	'Position',[20 h-150 100 150], ...
	'String', loadedNames, ...	
	'ListBoxTop', 1, ...
	'Style','listbox', ...
	'Max', 2, ...
	'Value', [], ...
	'userData', {comps,colors}, ...				% loaded userdata holds trajectory component count, color
	'callback', 'mview(''CFGTEMP'',''LOADED'')');
	
% displayed trajectories
uicontrol(cfg, ...			
	'Style', 'text', ...
	'HorizontalAlignment','left', ...
	'String', 'Displayed', ...
	'Position', [185 h 70 17]);
displayed = uicontrol(cfg, ...
	'Position',[175 h-150 100 150], ...	
	'String', displayedNames, ...	
	'Style','listbox', ...
	'Max', 2, ...
	'Value', [], ...
	'callback', 'mview(''CFGTEMP'',''DISPLAYED'')');

% xfer
h = height - 70;
xfer = uicontrol(cfg, ...
	'Position',[137 h 20 20], ...
	'enable', 'off', ...
	'String','>', ...
	'callback', 'mview(''CFGTEMP'',''XFER'')');

% delete
h = h - 30;
del = uicontrol(cfg, ...
	'Position',[137 h 20 20], ...
	'enable', 'off', ...
	'String','x', ...
	'callback', 'mview(''CFGTEMP'',''DELETE'')');

% move up
h = h - 30;
up = uicontrol(cfg, ...
	'Position',[137 h 20 20], ...
	'enable', 'off', ...
	'String','^', ...
	'callback', 'mview(''CFGTEMP'',''UPDN'',-1)');

% move down
h = h - 30;
dn = uicontrol(cfg, ...
	'Position',[137 h 20 20], ...
	'enable', 'off', ...
	'String','v', ...
	'callback', 'mview(''CFGTEMP'',''UPDN'',1)');

% content selection menu
h = height - 220;
uicontrol(cfg, ...			
	'Style', 'text', ...
	'HorizontalAlignment','right', ...
	'String', 'Content:', ...
	'Position', [20 h-1 70 17]);
content = uicontrol(cfg, ...
	'Style', 'popupmenu', ...
	'enable', 'off', ...
	'HorizontalAlignment', 'left', ...
	'String', ' ', ...
	'value', 1, ...
	'Position', [95 h 140 18], ...
	'callback', 'mview(''CFGTEMP'',''CONTENT'')');


% component selection buttons
h = h - 30;
uicontrol(cfg, ...			
	'Style', 'text', ...
	'HorizontalAlignment','right', ...
	'String', 'Components:', ...
	'Position', [55 h-1 70 17]);
xb = uicontrol(cfg, ...
	'Style', 'checkbox', ...
	'enable', 'off', ...
	'HorizontalAlignment', 'left', ...
	'String', 'X', ...
	'Value', 0, ...
	'Position', [130 h 33 18], ...
	'callback', 'mview(''CFGTEMP'',''XYZ'')');
yb = uicontrol(cfg, ...
	'Style', 'checkbox', ...
	'enable', 'off', ...
	'HorizontalAlignment', 'left', ...
	'String', 'Y', ...
	'Value', 0, ...
	'Position', [165 h 33 18], ...
	'callback', 'mview(''CFGTEMP'',''XYZ'')');
zb = uicontrol(cfg, ...
	'Style', 'checkbox', ...
	'enable', 'off', ...
	'HorizontalAlignment', 'left', ...
	'String', 'Z', ...
	'Value', 0, ...
	'Position', [200 h 33 18], ...
	'callback', 'mview(''CFGTEMP'',''XYZ'')');

% color selection
h = h - 30;
uicontrol(cfg, ...			
	'Style', 'text', ...
	'HorizontalAlignment','right', ...
	'String', 'Color:', ...
	'Position', [55 h-1 70 17]);
kb = uicontrol(cfg, ...
	'enable', 'off', ...
	'String', 'Select', ...
	'Position', [130 h 103 18], ...
	'callback', 'mview(''CFGTEMP'',''SETCOLOR'')');
defColor = get(kb, 'backgroundColor');

% OK/cancel buttons
uicontrol(cfg, ...
	'Position',[width/2-70 15 60 25], ...
	'String','OK', ...
	'Callback','set(gcbf,''UserData'',1);uiresume');
uicontrol(cfg, ...
	'Position',[width/2+10 15 60 25], ...
	'String','Cancel', ...
	'Callback','set(gcbf,''UserData'',0);uiresume');

% wait for input
set(cfg, 'userData', {loaded displayed content xfer del up dn xb yb zb kb defColor fh});
uiwait(cfg);
tempMap = [];
if ~ishandle(cfg), return; end;
if get(cfg, 'UserData'),
	tempMap = get(displayed, 'string');		% OK
end;
delete(cfg);


%=============================================================================
% TEMPENABLE  - control temporal panel enabling
%
%	usage:  TempEnable(content, xyz, loadedString, sel, compsColors, kb)
%
% called from CFGTEMP on single entry in displayed list selection

function TempEnable(content, xyz, loadedString, sel, compsColors, kb)

comps = compsColors{1};
colors = compsColors{2};
[ti, mod, comp] = ParseTempMap(loadedString, sel, comps);

% multi-component trajectories
if comps{ti} > 1,
	contentString = 'Movement|Velocity|Acceleration';
	contentVal = mod;
	set(xyz(1), 'enable', 'on', 'value', comp(1));
	set(xyz(2), 'enable', 'on', 'value', comp(2));
	if comps{ti} > 2,
		set(xyz(3), 'enable', 'on', 'value', comp(3));
	end;

% single-component trajectories
else,
	contentString = 'Signal|Spectrogram|F0|RMS|Zero Crossings|Velocity|Abs Vel';
	contentVal = mod;
	set(xyz, 'enable', 'off', 'value', 0);
end;

% set color button
set(kb, 'enable', 'on', 'backgroundColor', colors{ti}, 'userData', ti);

set(content, 'enable', 'on', ...
	'string', contentString, ...
	'value', contentVal, ...
	'userData', comps{ti});				% content userData holds # components this trajectory

	
%=============================================================================
% XORLINE  - create line object for animation
%
%	usage:  lh = xorline(...)
%
% for versions below 2014b uses 'eraseMode','xor'

function lh = xorline(varargin)

if verLessThan('matlab','8.4.0'),
	lh = line(varargin{:});
	set(lh, 'eraseMode','xor');
else,
	lh = line(varargin{:});
end
